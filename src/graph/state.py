from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # Identity
    run_id: str                          # set at initialisation
    dataset_id: str                      # the dataset being queried

    # Input
    question: str                        # the user's plain-English question
    messages: list[dict]                 # prior conversation turns [{role, content}, ...]

    # Dataset access (local only — used by profile/local_execute; NOT prompted)
    dataset_ref: Any                     # data.duckdb_engine.DatasetRef

    # Schema / profile (the ONLY dataset info given to the LLM, besides aggregates)
    schema: list[dict]                   # [{name, type}, ...] — column metadata
    profile: dict[str, Any]              # rows, null counts, basic per-column stats

    # Plan (from the plan node — LLM)
    plan_steps: list[str]                # human-readable plan steps
    generated_sql: str                   # DuckDB SQL drafted by the LLM

    # Local execution (raw rows — NEVER placed in any LLM prompt)
    query_rows: list[dict]               # raw result rows, local only
    query_columns: list[dict]            # result column metadata

    # Aggregates (the ONLY query data allowed past the privacy boundary)
    aggregates: dict[str, Any]           # summary numbers / small aggregate table

    # Narration (from the narrate node — LLM)
    answer: str                          # plain-language answer
    key_stats: list[dict]                # [{label, value, unit?}, ...] callouts
    chart_spec: dict[str, Any]           # {type, x, y, series, data} declarative chart
    summary_table: dict[str, Any]        # {columns: [...], rows: [...]}
    insight: str                         # written interpretation

    # Proactivity
    follow_ups: list[str]                # 2–3 suggested follow-up questions

    # Cost / observability
    prompt_tokens: int                   # summed across LLM calls this run
    completion_tokens: int               # summed across LLM calls this run
    est_usd: float                       # estimated USD for this run

    # Control
    status: str                          # set by finalize/handle_error
    error: str | None                    # set by any node on fatal failure
    checkpoint: str | None               # last completed node (for resume)
