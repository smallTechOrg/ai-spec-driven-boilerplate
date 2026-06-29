from graph.state import AgentState


def after_plan(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "execute_code"


def after_execute(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "format_response"
