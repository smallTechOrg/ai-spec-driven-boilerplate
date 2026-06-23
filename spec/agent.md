# Agent

## Agent Architecture Pattern

**Chosen:** Graph (LangGraph) — Prompt Chaining + Tool Use + Exception Handling.

A `StateGraph` with four sequential nodes and conditional error edges. Gemini 2.5 Flash is called once per query in `query_planner` with a forced `generate_sql` tool call (tool_config mode=ANY). The remaining nodes are non-LLM: SQL execution, response formatting, and audit logging. Conditional edges after `query_planner` and `sql_executor` route to `handle_error` on failure; all other edges are static.

Rationale: the task is a linear prompt-chain (plan SQL → execute → format → log) with one LLM call and one external tool. LangGraph provides structured state passing, explicit error routing, and easy extension for Phase 2 (chart formatting node). A plain script would not give the structured error-routing needed for clean 502 vs 403 responses.

---

## LLM Provider & Model

| Node | Provider | Model ID | Env var |
|------|----------|----------|---------|
| `query_planner` | Google Gemini | `gemini-2.5-flash` | `AGENT_LLM_MODEL` |

Only one LLM call per query. The model is configurable via `AGENT_LLM_MODEL`; the default is `gemini-2.5-flash`.

**Tool-use strategy:** `query_planner` calls Gemini with `tool_config={"function_calling_config": {"mode": "ANY"}}` so the model is forced to return a `generate_sql` function call — it cannot respond with plain text. This eliminates the need to parse free-form output.

**Retry:** `query_planner` retries the Gemini call up to 3 times on API error (exponential backoff, 1 s / 2 s / 4 s). After 3 failures it sets `state["error"]` and the conditional edge routes to `handle_error`.

**Prompt:** System prompt loaded from `src/prompts/query_planner.md`. Per-call user message: `[SCHEMA]\n{schema_context}\n\n[QUESTION]\n{question}`. Raw dataset rows are never included — schema context only (column names and SQLite types from PRAGMA table_info).

---

## Tools & Tool Calling

| Tool name | Description | Inputs | Output | Side-effects |
|-----------|-------------|--------|--------|--------------|
| `generate_sql` | Generate a SQLite SELECT query for the question | `sql: str` — the SQL statement | Extracted from function call response | None — SQL is extracted and passed to sql_executor |

The `generate_sql` tool is declared to Gemini as a function with a single `sql` string parameter. The node extracts `sql` from the function call response. Validation: the extracted SQL must begin with `SELECT` (case-insensitive); if not, the node sets `state["error"]` and routes to `handle_error`.

---

## Agent State

```python
from typing import TypedDict

class AnalystState(TypedDict, total=False):
    # Identity
    session_id: str          # set at invocation — browser-generated UUID
    dataset_table: str       # set at invocation — SQLite table name for this query

    # Input
    question: str            # user's natural-language question
    schema_context: str      # PRAGMA table_info result as formatted string

    # SQL pipeline
    sql: str                 # SQL string from Gemini generate_sql tool call
    sql_explanation: str     # brief plain-text explanation from query_planner (optional)
    rows: list[dict]         # list of row dicts from sql_executor (capped at 1000)
    row_count: int           # total rows returned by the query
    duration_ms: int         # sql_executor wall-clock time in milliseconds

    # Output
    answer: str              # markdown-formatted answer text from response_formatter
    table: list[dict]        # same as rows — passed through to API response
    audit_id: str            # UUID of the audit_log row written by audit_logger

    # Control
    error: str | None        # fatal error message — set by any node on failure
```

---

## Nodes

### `query_planner`

**Reads from state:** `question`, `dataset_table`, `session_id`

**Writes to state:** `schema_context`, `sql`, `sql_explanation` (optional), `error`

**LLM call:** Yes — Gemini 2.5 Flash with `generate_sql` tool forced (mode=ANY).

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | `PRAGMA table_info({dataset_table})` via SQLAlchemy text() | Sets state["error"], routes to handle_error |
| Gemini API | `generate_content` with generate_sql tool, mode=ANY | Retry 3× then sets state["error"] |

**Behaviour:**
1. Run `PRAGMA table_info({dataset_table})` to fetch column names and types.
2. Assemble `schema_context` string: `Table: {dataset_table}\nColumns:\n  - {col} ({type})\n  ...`
3. Call Gemini with system prompt + schema_context + question, tool_config mode=ANY.
4. Extract `sql` from the function call response.
5. Validate: `sql.strip().upper().startswith("SELECT")` — if not, set `state["error"] = "Invalid SQL: must be a SELECT statement."`.
6. On any Gemini API exception: retry up to 3× with backoff; after 3 failures set `state["error"]`.

---

### `sql_executor`

**Reads from state:** `sql`, `dataset_table`, `session_id`

**Writes to state:** `rows`, `row_count`, `duration_ms`, `error`

**LLM call:** No.

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | `sqlalchemy.text(state["sql"])` execute via session | Sets state["error"] with SQLAlchemy exception message |

**Behaviour:**
1. Record wall-clock start time.
2. Execute `sqlalchemy.text(state["sql"])` with the active SQLAlchemy session.
3. Fetch all rows; cap at 1,000. Convert to `list[dict]` using column keys from `result.keys()`.
4. Set `state["rows"]`, `state["row_count"]` (len of fetched rows, capped), `state["duration_ms"]`.
5. On SQLAlchemy exception: set `state["error"]` with the exception message.

> **Note:** No additional cross-session validation happens here — `query_planner` already validated the table prefix at the API layer before graph invocation.

---

### `response_formatter`

**Reads from state:** `sql_explanation`, `rows`, `row_count`, `sql`

**Writes to state:** `answer`, `table`

**LLM call:** No.

**External calls:** None.

**Behaviour:**
1. If `rows` is empty: set `answer = "No results found."`, `table = []`.
2. Otherwise: build a markdown answer. If `sql_explanation` is set, use it as the opening sentence. Append a summary line: "Returned {row_count} row(s)."
3. For each cell value: truncate strings longer than 50 characters to 50 chars + `…`. Render null/None as `—`.
4. Set `table = state["rows"]` (the capped list of dicts, with truncation applied to string values).
5. On any unexpected exception: set `answer = "Could not format result."`, `table = []`. Never sets `state["error"]` — this node is never fatal.

---

### `audit_logger`

**Reads from state:** `session_id`, `dataset_table`, `question`, `sql`, `row_count`, `duration_ms`, `error`

**Writes to state:** `audit_id`

**LLM call:** No.

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | INSERT into audit_log | Log warning via structlog; do not set state["error"] |

**Behaviour:**
1. Insert one row into `audit_log`: session_id, dataset_table, question, sql_generated (from `state.get("sql")`), row_count (None if error path), duration_ms (None if error path), error (from `state.get("error")`), created_at (UTC now).
2. Set `state["audit_id"]` to the inserted row's UUID.
3. Any exception during INSERT: log with structlog at WARNING level; do not propagate. The query response is never failed due to an audit write failure.

---

### `handle_error`

**Reads from state:** `error`, `session_id`

**Writes to state:** nothing (terminal node)

**LLM call:** No.

**External calls:** None (structlog only).

**Behaviour:**
1. Log `structlog.warning("graph_error", session_id=state["session_id"], error=state["error"])`.
2. This is a terminal node — the graph ends at END after this node.
3. The caller (FastAPI route) inspects `state["error"]` after graph completion and returns a 502 JSON response.

---

### `finalize`

**Reads from state:** `answer`, `table`, `sql`, `audit_id`

**Writes to state:** nothing (terminal node, no-op)

**LLM call:** No.

**External calls:** None.

**Behaviour:** No-op. Exists as an explicit terminal node on the happy path for symmetry with `handle_error` and to make the graph topology visually clear. The graph transitions to END after this node.

---

## Graph Topology

```
START
  │
  ▼
query_planner ──(error)──► handle_error ──► END
  │
  ▼  (no error)
sql_executor ──(error)──► handle_error ──► END
  │
  ▼  (no error)
response_formatter
  │
  ▼  (static edge — response_formatter never fails fatally)
audit_logger
  │
  ▼  (static edge)
finalize
  │
  ▼
END
```

**Conditional edges:**

| Source | Condition function | Targets |
|--------|--------------------|---------|
| `query_planner` | `after_plan(state)` | `"handle_error"` if `state.get("error")` else `"sql_executor"` |
| `sql_executor` | `after_execute(state)` | `"handle_error"` if `state.get("error")` else `"response_formatter"` |

**Static edges:**

| Source | Target |
|--------|--------|
| `response_formatter` | `audit_logger` |
| `audit_logger` | `finalize` |
| `finalize` | `END` |
| `handle_error` | `END` |

---

## Concurrency Model

- Each `POST /query` request invokes the graph as a synchronous call within FastAPI's thread pool (via `asyncio.to_thread` or `run_in_executor`). Each invocation is an independent `AnalystState` dict with no shared mutable state.
- No parallel nodes within a single run — the graph is fully sequential.
- No LangGraph checkpointer. State is not persisted between runs.
- Multiple concurrent requests from different sessions are safe: each uses its own SQLAlchemy session from the connection pool and its own `AnalystState`.

---

## Error Strategy

- **query_planner:** 3× retry on Gemini API error, then fatal (sets `state["error"]`). SQL validation failure is immediately fatal.
- **sql_executor:** any SQLAlchemy exception is fatal (sets `state["error"]`). No retry.
- **response_formatter:** never fatal. Falls back to "Could not format result." on any exception.
- **audit_logger:** never fatal. Logs warning on INSERT failure.
- **API layer (before graph):** Cross-session access (403) and missing `dataset_table` (422) are caught before the graph is invoked.

---

## Graph Assembly (`src/graph/agent.py`)

```python
from langgraph.graph import StateGraph, END
from src.graph.state import AnalystState
from src.graph.nodes import (
    query_planner,
    sql_executor,
    response_formatter,
    audit_logger,
    handle_error,
    finalize,
)
from src.graph.edges import after_plan, after_execute


def _build_graph() -> StateGraph:
    g = StateGraph(AnalystState)

    g.add_node("query_planner", query_planner)
    g.add_node("sql_executor", sql_executor)
    g.add_node("response_formatter", response_formatter)
    g.add_node("audit_logger", audit_logger)
    g.add_node("handle_error", handle_error)
    g.add_node("finalize", finalize)

    g.set_entry_point("query_planner")

    g.add_conditional_edges(
        "query_planner",
        after_plan,
        {
            "sql_executor": "sql_executor",
            "handle_error": "handle_error",
        },
    )
    g.add_conditional_edges(
        "sql_executor",
        after_execute,
        {
            "response_formatter": "response_formatter",
            "handle_error": "handle_error",
        },
    )

    g.add_edge("response_formatter", "audit_logger")
    g.add_edge("audit_logger", "finalize")
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)

    return g.compile()


analyst_graph = _build_graph()
```

Edge functions in `src/graph/edges.py`:

```python
def after_plan(state: AnalystState) -> str:
    return "handle_error" if state.get("error") else "sql_executor"

def after_execute(state: AnalystState) -> str:
    return "handle_error" if state.get("error") else "response_formatter"
```
