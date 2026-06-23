from typing import TypedDict


class AnalystState(TypedDict, total=False):
    # Identity
    session_id: str           # set at invocation — SQLite session UUID
    message_id: str           # set at invocation — new message UUID for this turn

    # Input
    question: str             # user's natural-language question
    conversation_history: list[dict]  # last N messages [{role, content}] from SQLite

    # Pipeline data (populated progressively by nodes)
    intent: str               # "data_query" | "clarification" | "off_topic" — set by classify_intent
    schema_context: str       # compact schema string — set by build_schema_context
    datasets: list[dict]      # [{"name": str, "file_path": str, "columns": [...]}] — set by build_schema_context
    sql: str | None           # SQL from Gemini tool call — set by call_llm_with_tools
    query_result: dict | None # QueryResultModel as dict — set by execute_query
    query_log_id: str | None  # UUID of QueryLog row — set by execute_query

    # Output
    narrative: str | None     # markdown narrative text — set by format_response
    chart_spec: dict | None   # ChartSpec as dict — set by format_response; None if no chart
    rich_response: dict | None  # RichResponseModel as dict — set by format_response

    # Control
    error: str | None         # fatal error message — set by any node on unrecoverable failure
    query_error: str | None   # DuckDB execution error — set by execute_query (recoverable errors)
    status: str               # "running" | "completed" | "failed" — updated by finalize/handle_error
