# Agent

Framework: **LangGraph** (already wired in `src/graph/`). The skeleton's `transform_text` node is replaced in place by the query pipeline below.

## Pattern

Phase 1 is a **linear pipeline with an error branch** (no loops): `load_schema → generate_sql → execute_sql → format_answer → finalize`, with any node failure routed to `handle_error`. The senior-analyst **plan→execute→critic→refine loop** is a Phase-4 evolution layered on the same graph (see below).

## State

`AgentState` (TypedDict, `total=False`) in `src/graph/state.py`:

| Field | Type | Set by |
|-------|------|--------|
| `run_id` | str | runner |
| `session_id` | str | runner |
| `dataset_id` | str | runner |
| `question` | str | runner |
| `schema` | list[dict] | `load_schema` — `[{name, type}]` |
| `table_name` | str | `load_schema` — DuckDB table |
| `sql` | str | `generate_sql` |
| `columns` | list[str] | `execute_sql` |
| `rows` | list[list] | `execute_sql` (full result, for the table) |
| `row_count` | int | `execute_sql` |
| `answer` | str | `format_answer` |
| `status` | str | `finalize` / `handle_error` |
| `error` | str \| None | any node on failure |

## Nodes

- **`load_schema`** — reads the `Dataset` row's stored schema JSON + DuckDB table name from the metadata DB. No LLM, no DuckDB rows.
- **`generate_sql`** — ONE Gemini call. Prompt = `src/prompts/sql_generate.md` (system) + rendered schema (`col: type` lines) + question. Returns a single read-only SELECT. Strips markdown fences.
- **`execute_sql`** — validates the statement is a single SELECT (reject otherwise), runs it read-only in DuckDB, captures `columns`/`rows`/`row_count`. Writes an `AuditLog` row (success or error) with `sql_text`, `status`, `row_count`, `duration_ms`. On DuckDB error sets `error`.
- **`format_answer`** — ONE Gemini call. Prompt = `src/prompts/format_answer.md` (system) + question + a capped preview (first 50 rows + total `row_count`). Returns prose. The full table is returned from `rows` (not via the LLM).
- **`handle_error`** — sets `status="failed"`, leaves `error` for the API to surface.
- **`finalize`** — sets `status="completed"`.

## Edges

```
entry → load_schema
load_schema   → generate_sql        (or handle_error if error)
generate_sql  → execute_sql         (or handle_error if error)
execute_sql   → format_answer       (or handle_error if error)
format_answer → finalize            (or handle_error if error)
finalize      → END
handle_error  → END
```

Each forward edge is a conditional edge keyed on `state.get("error")`: a shared `route(state)` helper in `src/graph/edges.py` returns `"handle_error"` when `error` is set, else the next node name.

## Error handler & finalize

`handle_error` and `finalize` are terminal nodes both wired to `END`. The runner persists `answer`, `sql`, table, and `status` to a `Message` and updates the `Run` row.

## Concurrency

Single-threaded per request (one graph invocation per query). DuckDB query execution is read-only; the store uses one shared connection guarded by a lock for thread safety under concurrent API requests.

## Graph assembly (pseudocode)

```python
g = StateGraph(AgentState)
g.add_node("load_schema", load_schema)
g.add_node("generate_sql", generate_sql)
g.add_node("execute_sql", execute_sql)
g.add_node("format_answer", format_answer)
g.add_node("handle_error", handle_error)
g.add_node("finalize", finalize)
g.set_entry_point("load_schema")
for src, nxt in [("load_schema","generate_sql"),
                 ("generate_sql","execute_sql"),
                 ("execute_sql","format_answer"),
                 ("format_answer","finalize")]:
    g.add_conditional_edges(src, route(nxt), {nxt: nxt, "handle_error": "handle_error"})
g.add_edge("finalize", END)
g.add_edge("handle_error", END)
agentic_ai = g.compile()
```

## Planned evolution — senior-analyst multi-step loop (Phase 4)

Add `plan` (decompose into ordered sub-queries) and `critic` (inspect a failed/empty SQL result and propose a fix) nodes. A `complexity_gate` after `load_schema` routes simple questions straight to `generate_sql` (preserving the two-call happy path) and complex ones into `plan → generate_sql → execute_sql → critic → (refine | format_answer)` with a bounded retry count (max 3) to cap tokens. The linear Phase-1 graph is the inner happy path of this loop.
