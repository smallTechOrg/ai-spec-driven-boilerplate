"""Conditional routing functions for the LangGraph agent."""

from sourcing_agent.domain.models import SourcingRunStatus
from sourcing_agent.graph.state import AgentState


def route_after_intake(state: AgentState) -> str:
    if state.get("status") == SourcingRunStatus.FAILED:
        return "error_handler"
    return "research"


def route_after_research(state: AgentState) -> str:
    if state.get("status") == SourcingRunStatus.FAILED:
        return "error_handler"
    return "rank"


def route_after_rank(state: AgentState) -> str:
    if state.get("status") == SourcingRunStatus.FAILED:
        return "error_handler"
    return "__end__"
