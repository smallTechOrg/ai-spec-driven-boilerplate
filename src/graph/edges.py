from config.settings import get_settings
from graph.state import AgentState


def after_execute(state: AgentState) -> str:
    """Route after the local sandbox runs: success -> explain, recoverable error
    -> one more repair pass (bounded by react_max_steps), exhausted -> graceful
    failure. A fatal `error` short-circuits straight to handle_error."""
    if state.get("error"):
        return "handle_error"
    if state.get("exec_error"):
        if state.get("repair_attempts", 0) < get_settings().react_max_steps:
            return "propose_code"          # feed the error back for one repair
        return "handle_error"              # budget exhausted -> graceful failure
    return "explain_result"


def after_transform(state: AgentState) -> str:
    # Kept for the bare transform_text capability slot.
    if state.get("error"):
        return "handle_error"
    return "finalize"


def after_react(state: AgentState) -> str:
    if state.get("error"):
        return "handle_error"
    # More tool calls queued and budget holds → loop; else we have an answer.
    if state.get("messages") and state["messages"][-1].get("role") == "user":
        # last turn is tool results → the model must observe them
        return "react"
    return "guard_output"
