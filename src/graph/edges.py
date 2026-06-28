from graph.state import AgentState


def route_after_verify(state: AgentState) -> str:
    """Decide the next node after verify.

    - fatal error (e.g. dataset load / LLM failure) -> handle_error
    - valid result                                  -> finalize
    - recoverable error AND step < max_steps        -> plan (retry)
    - recoverable error AND step >= max_steps        -> handle_error (cap hit)
    """
    if state.get("error"):
        return "handle_error"

    if not state.get("last_error") and state.get("exec_result") is not None:
        return "finalize"

    step = state.get("step", 0)
    max_steps = state.get("max_steps", 4)
    if step + 1 < max_steps:
        return "plan"
    return "handle_error"


def increment_step(state: AgentState) -> AgentState:
    """Bump the loop counter before re-planning."""
    return {**state, "step": state.get("step", 0) + 1}
