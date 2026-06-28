"""Conditional edge routers for the analysis graph."""

from __future__ import annotations

from graph.state import AgentState

MAX_RETRIES = 1


def route_on_error(state: AgentState, next_node: str) -> str:
    """Route to handle_error if the node set an error, else to next_node."""
    return "handle_error" if state.get("error") else next_node


def route_after_execute(state: AgentState) -> str:
    """After execute_local: self-correct once, else continue to visualize.

    - traceback + retries left -> generate_code (self-correction)
    - traceback + no retries   -> visualize (best-guess, degraded)
    - success                  -> visualize
    """
    if state.get("error"):
        return "handle_error"
    if state.get("traceback"):
        if state.get("retry_count", 0) < MAX_RETRIES:
            return "generate_code"
        return "visualize"
    return "visualize"
