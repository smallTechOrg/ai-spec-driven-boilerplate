from langgraph.graph import END

from graph.state import AgentState


def after_clarification(state: AgentState) -> str:
    if state.get("action") == "clarification":
        return END
    return "plan_and_code"


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
