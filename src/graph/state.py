from typing import TypedDict


class NodeTrace(TypedDict):
    node: str
    duration_ms: float


class AgentState(TypedDict, total=False):
    # Identity
    run_id: str
    dataset_id: str                      # which uploaded dataset to analyse
    conversation_id: str                 # = dataset_id from Phase 2 (session memory key); blank in P1

    # Input
    input_text: str                      # legacy transform_text slot (off the analysis path)
    question: str                        # the user's natural-language question

    # Dataset (LOCAL — full df never leaves the box)
    df_path: str                         # local path data/uploads/<dataset_id>.csv
    schema: list[dict]                   # [{name, dtype}] derived locally
    sample: dict                         # {preview_rows, summary} — bounded
    row_count: int

    # Plan / execute / explain
    proposed_code: str                   # the pandas snippet the LLM proposed (assigns `result`)
    code_result: object                  # JSON-serializable value captured from the sandbox
    exec_error: str | None               # structured sandbox error (drives the repair loop)
    repair_attempts: int                 # bounded by react_max_steps
    explanation: str                     # plain-language explanation of code_result

    # ReAct loop (legacy transform/react seam — off the analysis path)
    messages: list[dict]                 # provider-shaped running history
    iterations: int                      # THE loop counter (react owns it; budget reads it)

    # Memory
    memory_context: str                  # session transcript, fenced as untrusted

    # Output
    output_text: str                     # legacy transform_text slot (off the analysis path)
    answer: str                          # human-readable numeric answer string
    code: str                            # = proposed_code that actually produced the result

    # Observability — populated progressively by nodes
    tokens_in: int
    tokens_out: int
    cost_usd: float
    model: str
    node_trace: list[NodeTrace]

    # Control
    error: str | None
    guard_code: str | None               # machine-readable guard verdict
    status: str
