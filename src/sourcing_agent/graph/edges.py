from __future__ import annotations

from sourcing_agent.graph.state import AgentState


def after_research(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "enrich"


def after_enrich(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "score"


def after_score(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "finalize"
