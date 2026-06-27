from graph.agent import agentic_ai
from graph.state import AgentState
from db.session import create_db_session, init_db
from db.models import RunRow
from observability.events import get_logger

logger = get_logger("graph.runner")


def run_agent(dataset_id: str, question: str) -> str:
    """Answer one question about a dataset and persist the run.

    Creates a ``RunRow`` (status ``pending``), invokes the LangGraph pipeline
    (load_profile -> build_prompt -> answer -> finalize / handle_error), then
    persists the outcome (``status``, ``output_text``, ``error_message``) to the
    row. Returns the ``run_id``. Never raises on a model/data failure — those are
    recorded as a ``failed`` run with human-readable copy.
    """
    init_db()

    with create_db_session() as session:
        run = RunRow(
            input_text=question,
            dataset_id=dataset_id,
            status="pending",
        )
        session.add(run)
        session.flush()
        run_id = run.id

    initial: AgentState = {
        "run_id": run_id,
        "dataset_id": dataset_id,
        "question": question,
        "error": None,
    }
    final = agentic_ai.invoke(initial)

    status = final.get("status", "failed")
    with create_db_session() as session:
        run = session.get(RunRow, run_id)
        run.status = status
        run.output_text = final.get("answer")
        run.error_message = final.get("error")

    logger.info("run_outcome", run_id=run_id, dataset_id=dataset_id, status=status)
    return run_id
