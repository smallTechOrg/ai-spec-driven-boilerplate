from data_analysis_agent.graph.state import AgentState


def after_load_data(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "analyze"


def after_analyze(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "finalize"


def after_finalize(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "end"
