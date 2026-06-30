from langgraph.graph import END

from graph.state import AgentState


def after_clarification(state: AgentState) -> str:
    """Phase 4 edge: routes to inspect_quality before plan_and_code."""
    if state.get("action") == "clarification":
        return END
    return "inspect_quality"


# Alias for explicitness — used interchangeably with after_clarification in Phase 4+
after_clarification_p4 = after_clarification


def after_plan(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "execute_code"


def after_execute(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "format_response"


def after_execute_p3(state: AgentState) -> str:
    """After execute_code: retry via reflection if failed, up to 2 times."""
    if not state.get("error"):
        return "format_response"
    retry_count = state.get("retry_count", 0)
    if retry_count < 2:
        return "reflect_and_retry"
    return "handle_error"
