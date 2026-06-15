import structlog

from data_analysis_agent.graph.agent import agent_graph
from data_analysis_agent.graph.state import AgentState
from data_analysis_agent.db.session import create_db_session, init_db
from data_analysis_agent.db.models import QueryRecordRow, AgentRunRow

log = structlog.get_logger()


def run_pipeline(
    query_record_id: str,
    dataset_id: str,
    question: str,
    csv_path: str,
) -> AgentState:
    init_db()

    with create_db_session() as session:
        run = AgentRunRow(query_record_id=query_record_id)
        session.add(run)
        session.flush()
        run_id = run.id

    initial: AgentState = {
        "run_id": run_id,
        "query_record_id": query_record_id,
        "dataset_id": dataset_id,
        "question": question,
        "csv_path": csv_path,
        "error": None,
    }

    log.info("pipeline.start", run_id=run_id, query_record_id=query_record_id)
    final = agent_graph.invoke(initial)
    log.info("pipeline.complete", run_id=run_id, status="done")
    return final
