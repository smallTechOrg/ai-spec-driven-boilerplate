from typing import TypedDict


class AgentState(TypedDict, total=False):
    # Identity
    run_id: str
    conversation_id: str

    # Input
    question: str
    dataset_id: str
    history: list  # [{role, content}] prior turns (conversation memory)

    # Context (built server-side; privacy-safe — schema/stats/sample only)
    profile: dict
    column_notes: list  # (P4)

    # Pipeline data (populated progressively by nodes)
    plan: str
    code: str
    execution: dict  # ExecutionResult: {result_preview, stdout, error}
    iteration: int
    verdict: str  # "done" | "refine" | "clarify"
    difficulty: str  # (P4)

    # Output
    answer: str
    suggestions: list
    chart_spec: dict  # (P3)
    clarifying_question: str  # (P4)

    # Cost / observability
    tokens: dict  # {prompt, completion}
    cost_usd: float

    # Control
    error: str | None
    status: str  # "completed" | "failed" | "needs_clarification"

    # Internal (server-side only; NEVER sent to the LLM). The full in-memory
    # DataFrame is carried here so execute_code runs against the full data
    # without re-reading the file each refine pass.
    _df: object
