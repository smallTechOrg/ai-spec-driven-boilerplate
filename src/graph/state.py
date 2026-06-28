from typing import TypedDict, Any


class AgentState(TypedDict, total=False):
    # Identity
    run_id: str
    session_id: str | None

    # Input
    file_id: str
    question: str
    source_type: str  # "csv" | "excel" | "postgres"

    # Pipeline data (populated progressively by nodes)
    file_path: str
    df: Any  # pandas DataFrame
    schema_info: dict  # {columns, dtypes, sample_rows}
    generated_code: str
    code_type: str  # "pandas" | "sql"
    result_sample: str  # ≤500 rows as CSV string

    # Output
    answer_text: str
    chart_spec: dict | None

    # Phase 3 extension
    conversation_history: list  # [{question, answer_text, chart_spec}, ...] prior turns

    # Control
    error: str | None
    status: str

    # Legacy fields (retained for backward compat with /runs skeleton endpoint)
    input_text: str
    output_text: str
    messages: list
