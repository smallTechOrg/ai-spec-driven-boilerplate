"""run_agent() — entry point called by the FastAPI route."""
from __future__ import annotations

from lead_gen_agent.db import init_db
from lead_gen_agent.domain import SearchCriteria
from lead_gen_agent.graph.agent import compiled_graph
from lead_gen_agent.graph.state import AgentState


def run_agent(run_id: str, criteria: SearchCriteria) -> AgentState:
    """Execute the lead-gen pipeline synchronously. Returns final state."""
    init_db()
    initial_state: AgentState = {
        "run_id": run_id,
        "criteria": criteria,
        "raw_companies": [],
        "leads": [],
        "error": None,
    }
    final_state = compiled_graph.invoke(initial_state)
    return final_state
