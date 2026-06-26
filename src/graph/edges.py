from graph.state import AgentState


def after_load(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "analyze_query"


def after_analyze(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "extract_table"


# Keep old name for any leftover imports
def after_transform(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "finalize"
