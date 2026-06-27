import time

from graph.agent import agentic_ai, legacy_agentic_ai
from graph.state import AgentState
from db.session import create_db_session, init_db
from db.models import DatasetRow, QueryRow, RunRow
from observability.events import get_logger

_log = get_logger("runner")


def run_agent(input_text: str, conversation_id: str = "") -> str:
    init_db()

    with create_db_session() as session:
        run = RunRow(input_text=input_text)
        session.add(run)
        session.flush()
        run_id = run.id

    _log.info("run.start", run_id=run_id)
    t0 = time.monotonic()

    initial: AgentState = {
        "run_id": run_id,
        "conversation_id": conversation_id,
        "input_text": input_text,
        "error": None,
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
        "iterations": 0,
        "messages": [],
        "node_trace": [],
    }
    final = legacy_agentic_ai.invoke(initial)

    latency_ms = round((time.monotonic() - t0) * 1000, 2)
    _log.info(
        "run.persisted",
        run_id=run_id,
        status=final.get("status", "completed"),
        latency_ms=latency_ms,
        tokens_in=final.get("tokens_in", 0),
        tokens_out=final.get("tokens_out", 0),
        cost_usd=final.get("cost_usd", 0.0),
    )

    with create_db_session() as session:
        run = session.get(RunRow, run_id)
        run.status = final.get("status", "completed")
        run.output_text = final.get("output_text")
        run.error_message = final.get("error")
        run.tokens_in = final.get("tokens_in", 0)
        run.tokens_out = final.get("tokens_out", 0)
        run.cost_usd = final.get("cost_usd", 0.0)
        run.latency_ms = latency_ms
        run.model = final.get("model")
        run.node_trace = final.get("node_trace", [])
        run.guard_code = final.get("guard_code")

    return run_id


def run_query(dataset_id: str, question: str, conversation_id: str = "") -> dict:
    """Run one analysis query against an uploaded dataset.

    Resolves the dataset's local file path, runs the analysis graph
    (plan -> execute -> explain with a bounded repair loop), persists exactly one
    QueryRow (the auditable record — single write point covering both the
    completed and failed terminals), and returns the dict the API will wrap.
    """
    init_db()

    with create_db_session() as session:
        dataset = session.get(DatasetRow, dataset_id)
        if dataset is None:
            df_path = None
        else:
            df_path = dataset.file_path

    t0 = time.monotonic()

    if df_path is None:
        # Dataset not found — persist a failed QueryRow and return gracefully.
        latency_ms = round((time.monotonic() - t0) * 1000, 2)
        error = "Dataset not found. Please upload a CSV first."
        with create_db_session() as session:
            row = QueryRow(
                dataset_id=dataset_id,
                conversation_id=conversation_id,
                question=question,
                status="failed",
                error_message=error,
                latency_ms=latency_ms,
            )
            session.add(row)
            session.flush()
            query_id = row.id
        _log.error("run.failed", dataset_id=dataset_id, error=error)
        return {
            "query_id": query_id, "dataset_id": dataset_id, "status": "failed",
            "answer": None, "explanation": None, "code": None, "result": None,
            "error": error, "model": None, "tokens_in": 0, "tokens_out": 0,
            "cost_usd": 0.0, "latency_ms": latency_ms,
        }

    _log.info("run.start", dataset_id=dataset_id)

    initial: AgentState = {
        "dataset_id": dataset_id,
        "conversation_id": conversation_id,
        "question": question,
        "df_path": df_path,
        "error": None,
        "exec_error": None,
        "repair_attempts": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
        "node_trace": [],
    }
    final = agentic_ai.invoke(initial)

    latency_ms = round((time.monotonic() - t0) * 1000, 2)
    status = final.get("status", "completed")
    error = final.get("error")

    with create_db_session() as session:
        row = QueryRow(
            dataset_id=dataset_id,
            conversation_id=conversation_id,
            question=question,
            code=final.get("code"),
            result_json=final.get("code_result"),
            explanation=final.get("explanation"),
            answer=final.get("answer"),
            status=status,
            error_message=error,
            repair_attempts=final.get("repair_attempts", 0),
            tokens_in=final.get("tokens_in", 0),
            tokens_out=final.get("tokens_out", 0),
            cost_usd=final.get("cost_usd", 0.0),
            latency_ms=latency_ms,
            model=final.get("model"),
            node_trace=final.get("node_trace", []),
            guard_code=final.get("guard_code"),
        )
        session.add(row)
        session.flush()
        query_id = row.id

    _log.info(
        "query.persisted", query_id=query_id, dataset_id=dataset_id, status=status,
        latency_ms=latency_ms, tokens_in=final.get("tokens_in", 0),
        tokens_out=final.get("tokens_out", 0), cost_usd=final.get("cost_usd", 0.0),
        model=final.get("model"), repair_attempts=final.get("repair_attempts", 0),
    )

    return {
        "query_id": query_id,
        "dataset_id": dataset_id,
        "status": status,
        "answer": final.get("answer"),
        "explanation": final.get("explanation"),
        "code": final.get("code"),
        "result": final.get("code_result"),
        "error": error,
        "model": final.get("model"),
        "tokens_in": final.get("tokens_in", 0),
        "tokens_out": final.get("tokens_out", 0),
        "cost_usd": final.get("cost_usd", 0.0),
        "latency_ms": latency_ms,
    }
