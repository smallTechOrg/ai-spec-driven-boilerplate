from graph.state import AgentState


def after_inspect(state: AgentState) -> str:
    """P1: always finalize (single pass). P3: retry when inspect requests it and
    the step cap has not been reached."""
    decision = state.get("inspect_decision", "answer")
    step = int(state.get("step", 0))
    max_steps = int(state.get("max_steps", 4))
    if decision == "retry" and step < max_steps:
        return "generate_code"
    return "finalize"
