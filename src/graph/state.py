from typing import TypedDict


class AgentState(TypedDict, total=False):
    run_id: str               # analyses row id
    dataset_id: str           # active dataset
    storage_path: str         # local CSV path — NOT data-derived, never in a prompt
    question: str             # user's plain-language question

    # Data-derived content ALLOWED in LLM prompts (schema/sample/aggregates only):
    schema: dict              # column names + dtypes
    sample: list              # bounded row sample
    aggregates: dict          # per-column aggregates

    plan: str                 # current step's intent
    code: str                 # latest LLM-generated pandas code
    exec_result: dict | None  # serialized result of local execution
    chart_spec: dict | None   # Vega-Lite spec
    answer: str               # final prose answer

    step: int                 # loop counter (0-based attempts)
    steps_taken: int          # iterations used (reported)
    max_steps: int            # step cap
    error_message: str | None # failure message persisted to audit
    last_error: str | None    # execution/verify error fed back to codegen
    status: str               # running | completed | failed
    error: str | None         # fatal error message
    messages: list            # chat-turn history (Phase 2+)
