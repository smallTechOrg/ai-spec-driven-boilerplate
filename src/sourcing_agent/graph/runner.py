from __future__ import annotations

from sourcing_agent.config.settings import get_settings
from sourcing_agent.db.models import RunRow, SourcingRequestRow
from sourcing_agent.db.session import create_db_session, init_db
from sourcing_agent.graph.agent import agent_graph
from sourcing_agent.graph.state import AgentState


def run_agent(request_id: str) -> str:
    """Run the sourcing graph for an existing SourcingRequest. Returns run_id."""
    init_db()
    settings = get_settings()

    with create_db_session() as session:
        req = session.get(SourcingRequestRow, request_id)
        if req is None:
            raise ValueError(f"unknown request_id: {request_id}")
        request_dict = {
            "id": req.id,
            "material": req.material,
            "quantity": req.quantity,
            "location": req.location,
            "budget": req.budget,
            "timeline": req.timeline,
            "criteria": req.criteria,
        }
        run = RunRow(
            request_id=req.id,
            status="running",
            llm_provider=settings.resolved_llm_provider,
            search_provider=settings.resolved_search_provider,
        )
        session.add(run)
        session.flush()
        run_id = run.id

    initial: AgentState = {
        "run_id": run_id,
        "request_id": request_id,
        "request": request_dict,
        "error": None,
    }
    agent_graph.invoke(initial)
    return run_id
