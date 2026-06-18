from data_analyst.graph.state import AgentState
from data_analyst.config.settings import get_settings


def after_setup(state: AgentState) -> str:
    if state.get("error"):
        return "handle_error"
    return "plan_action"


def after_plan_action(state: AgentState) -> str:
    max_iter = get_settings().max_iterations

    if state.get("iteration_count", 0) >= max_iter:
        return "force_finalize"

    if state.get("error"):
        return "handle_error"

    response = (state.get("llm_response") or "").strip()
    if "FINAL ANSWER:" in response.upper():
        return "finalize"

    return "execute_action"
