"""Query runner: creates the queries row, runs the graph, persists the result."""
import json

from db.models import Dataset, Query
from db.session import create_db_session
from graph.agent import agentic_ai
from graph.state import AgentState


def run_query(dataset_id: str, question: str) -> str:
    """Run a NL question against a dataset synchronously. Returns the query id.

    The caller is responsible for having validated that the dataset exists and
    that the question is non-empty.
    """
    # Load cached schema/sample + table name (NO full rows).
    with create_db_session() as session:
        ds = session.get(Dataset, dataset_id)
        if ds is None:
            raise ValueError(f"Dataset {dataset_id} not found")
        table_name = ds.table_name
        schema_text = ds.schema_text
        sample_text = ds.sample_text

        q = Query(dataset_id=dataset_id, question=question, status="pending")
        session.add(q)
        session.flush()
        query_id = q.id

    initial: AgentState = {
        "query_id": query_id,
        "dataset_id": dataset_id,
        "table_name": table_name,
        "question": question,
        "schema_text": schema_text,
        "sample_text": sample_text,
        "error": None,
    }

    try:
        final: AgentState = agentic_ai.invoke(initial)
    except Exception as exc:  # noqa: BLE001 - never let a graph crash escape
        final = {**initial, "status": "failed", "error": f"Graph error: {exc}"}

    status = final.get("status") or ("failed" if final.get("error") else "completed")

    with create_db_session() as session:
        q = session.get(Query, query_id)
        q.generated_sql = final.get("generated_sql")
        q.answer_text = final.get("answer_text")
        result_columns = final.get("result_columns")
        result_rows = final.get("result_rows")
        q.result_columns_json = (
            json.dumps(result_columns) if result_columns is not None else None
        )
        q.result_rows_json = (
            json.dumps(result_rows, default=str) if result_rows is not None else None
        )
        q.row_count = final.get("row_count")
        q.status = status
        q.error_message = final.get("error")

    return query_id
