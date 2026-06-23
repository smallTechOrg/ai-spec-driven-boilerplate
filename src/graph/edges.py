from graph.state import AgentState


def after_generate_sql(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "execute_sql"


def after_execute_sql(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "compose_answer"


def after_compose_answer(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "finalize"
