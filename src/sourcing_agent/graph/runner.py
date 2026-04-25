"""Runner — entry point for executing a sourcing run through the agent graph."""

import logging
import uuid

from sourcing_agent.db.session import init_db
from sourcing_agent.domain.models import SourcingRunStatus
from sourcing_agent.graph.agent import get_graph
from sourcing_agent.graph.state import AgentState

logger = logging.getLogger(__name__)


def run_agent(run_id: uuid.UUID) -> AgentState:
    """Execute the sourcing pipeline for the given run_id.

    Initialises DB tables (idempotent) then runs the LangGraph graph.
    Returns the final AgentState.
    """
    init_db()
    graph = get_graph()

    initial_state: AgentState = {
        "run_id": str(run_id),
        "project_name": "",
        "materials": [],
        "supplier_candidates": {},
        "recommendations": {},
        "status": SourcingRunStatus.PENDING,
        "error": None,
    }

    logger.info("Starting sourcing run %s", run_id)
    final_state: AgentState = graph.invoke(initial_state)
    logger.info("Completed sourcing run %s — status=%s", run_id, final_state.get("status"))
    return final_state
