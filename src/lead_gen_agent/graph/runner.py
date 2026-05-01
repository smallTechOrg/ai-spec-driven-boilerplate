from __future__ import annotations

from lead_gen_agent.db import repository as repo
from lead_gen_agent.db.session import create_db_session, init_db
from lead_gen_agent.graph.agent import agent_graph
from lead_gen_agent.graph.state import AgentState


def run_pipeline(country: str, industry: str, size_band: str) -> str:
    init_db()
    filters = {"country": country, "industry": industry, "size_band": size_band}
    with create_db_session() as s:
        run_id = repo.create_run(s, filters)

    initial: AgentState = {
        "run_id": run_id,
        "country": country,
        "industry": industry,
        "size_band": size_band,
        "error": None,
    }
    agent_graph.invoke(initial)
    return run_id
