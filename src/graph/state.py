from typing import TypedDict


class AgentState(TypedDict, total=False):
    # Identity — set by the runner at init.
    run_id: str

    # Input — set by the runner from the request.
    dataset_id: str
    question: str

    # Pipeline data — populated progressively by the nodes.
    profile: dict          # set by load_profile (LOCAL pandas) — schema + stats + examples
    prompt: str            # set by build_prompt — the EXACT user-prompt string sent to the LLM
                           #   (question + profile ONLY; asserted to contain no raw rows)

    # Output.
    answer: str            # set by the answer node from the Gemini response
    status: str            # set by finalize/handle_error: "completed" | "failed"

    # Control.
    error: str | None      # set by any node on fatal failure
    messages: list         # unused in Phase 1 (kept from skeleton for compatibility)
