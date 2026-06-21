"""AgentState — the working memory of one run.

WARNING: ``tool_call_history`` is a PLAIN list — there is NO ``Annotated[list,
add_messages]`` reducer. The graph nodes return the full updated list themselves
(``history + [...]``); an add_messages reducer would double-append and corrupt the
transcript. Keep it a plain list.
"""

from typing import Any, TypedDict


class AgentState(TypedDict):
    # Identity
    run_id: int

    # Input (set at run start)
    user_input: str

    # Pipeline data (populated progressively by nodes)
    tool_call_history: list[dict[str, Any]]
    result: str | None

    # Control
    error: str | None  # set by any node on fatal failure
    iterations: int    # incremented by plan_action; guards against infinite loops
