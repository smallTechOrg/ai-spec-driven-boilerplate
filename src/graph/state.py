from typing import TypedDict


class AgentState(TypedDict, total=False):
    # Identity
    query_id: str            # queries row id
    dataset_id: str
    table_name: str          # "ds_<dataset_id>"

    # Input
    question: str
    schema_text: str         # cached schema string (NO full rows)
    sample_text: str         # cached ≤20-row sample string

    # Pipeline data
    generated_sql: str
    result_columns: list[str]
    result_rows: list[list]
    row_count: int
    duration_ms: int

    # Output
    answer_text: str
    status: str              # "completed" | "failed"

    # Control
    error: str | None
