from graph.agent import agentic_ai
from graph.state import AgentState
from db.session import create_db_session, init_db
from db.models import RunRow
import json


def run_agent(session_id: str, dataset_id: str, question: str) -> dict:
    """Run the analyst graph. Returns dict with answer_text, table_data, chart_b64, error, status."""
    init_db()

    with create_db_session() as session:
        run = RunRow(
            session_id=session_id,
            dataset_id=dataset_id,
            question=question,
            input_text=question,
        )
        session.add(run)
        session.flush()
        run_id = run.id

    initial: AgentState = {
        "run_id": run_id,
        "session_id": session_id,
        "dataset_id": dataset_id,
        "question": question,
        "error": None,
        "table_data": None,
        "chart_b64": None,
    }
    final = agentic_ai.invoke(initial)

    answer_text = final.get("answer_text")
    table_data = final.get("table_data")
    error = final.get("error")
    status = final.get("status", "completed")

    with create_db_session() as session:
        run = session.get(RunRow, run_id)
        run.status = status
        run.answer_text = answer_text
        run.output_text = answer_text
        run.table_json = json.dumps(table_data) if table_data is not None else None
        run.error_message = error

    return {
        "run_id": run_id,
        "status": status,
        "answer_text": answer_text,
        "table_data": table_data,
        "chart_b64": None,
        "error": error,
    }
