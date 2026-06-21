from typing import Any, TypedDict


class AgentState(TypedDict):
    # Identity
    run_id: int

    # Input (set at run start)
    user_input: str

    # Pipeline data (populated progressively by nodes).
    # NOTE: tool_call_history is a PLAIN list — there is no add_messages reducer.
    # Each node returns the full updated list; LangGraph replaces the value
    # wholesale. Don't expect messages to be appended/merged automatically.
    tool_call_history: list[dict[str, Any]]
    result: str | None

    # Control
    error: str | None          # set by any node on fatal failure
    iterations: int            # incremented by plan_action; guards against infinite loops
