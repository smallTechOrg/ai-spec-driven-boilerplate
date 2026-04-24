"""Conditional routing functions."""
from __future__ import annotations

from lead_gen_agent.graph.state import AgentState


def route_on_error(state: AgentState) -> str:
    """If error is set, route to handle_error; otherwise continue to next node."""
    return "handle_error" if state.get("error") else "continue"
