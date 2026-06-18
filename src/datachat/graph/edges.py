"""Conditional routing functions for the ReAct graph (07-agent-graph.md)."""

from __future__ import annotations

from datachat.config.settings import get_settings
from datachat.graph.state import AgentState

_REPEATED_ERROR_LIMIT = 3


def _last_n_errored(state: AgentState, n: int = _REPEATED_ERROR_LIMIT) -> bool:
    history = state.get("action_history", [])
    if len(history) < n:
        return False
    return all(step.get("is_error") for step in history[-n:])


def route_after_context(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "plan_action"


def route_after_plan(state: AgentState) -> str:
    if state.get("error"):
        return "handle_error"
    if state["last_tool_call"].get("name") == "finish":
        return "finalize"
    if state.get("iteration_count", 0) >= get_settings().max_iterations or _last_n_errored(state):
        return "force_finalize"
    return "execute_action"
