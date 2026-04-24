"""run_agent() — entry point called by the FastAPI route."""
from __future__ import annotations

from lead_gen_agent.db import init_db
from lead_gen_agent.domain import SearchCriteria
from lead_gen_agent.graph.agent import compiled_graph
from lead_gen_agent.graph.progress import close_run
from lead_gen_agent.graph.state import AgentState


def run_agent(run_id: str, criteria: SearchCriteria) -> AgentState:
    """Execute the lead-gen pipeline synchronously. Returns final state.

    The caller (FastAPI route) must call register_run(run_id) before invoking
    this function in a background thread. close_run() is always called here.
    """
    init_db()
    initial_state: AgentState = {
        "run_id": run_id,
        "criteria": criteria,
        "raw_companies": [],
        "leads": [],
        "error": None,
    }
    try:
        final_state = compiled_graph.invoke(initial_state)
    finally:
        close_run(run_id)
    return final_state
