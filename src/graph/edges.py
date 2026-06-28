"""Conditional edge routing functions for the Data Analysis Agent graph."""

from graph.state import AgentState


def after_load(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "plan_analysis"


def after_plan(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "execute_code"


def after_execute(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "reason_answer"


def after_reason(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "finalize"
