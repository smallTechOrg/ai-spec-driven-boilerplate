# Agent

---

## Agent Architecture Pattern

| Pattern | Use when |
|---------|----------|
| **Graph (LangGraph)** | Multi-step pipeline with conditional edges, checkpointing, or parallel nodes. |

**Chosen:** Graph (LangGraph) as a deterministic **Prompt Chaining + Tool Use** pipeline — `profile_schema → generate_sql → execute_sql → narrate` — with **Exception Handling** (any node sets `error` and routes to `handle_error`) and **Resource-Aware Optimization** as a first-class constraint (the `profile_schema` node is the token-economy guard). Catalogue refs in `harness/patterns/agentic-ai.md`: #1 Prompt Chaining, #5 Tool Use, #12 Exception Handling, #16 Resource-Aware Optimization. A fixed chain (not a single tool-loop) is chosen because the steps are ordered and dependent, and isolating SQL generation from execution lets us validate/guard each boundary. The senior-analyst clarify/plan/recommend loop (Routing/HITL/Planning, catalogue #2/#13/#6) is a deliberate Phase-3 expansion, noted under Graph Topology.

---

## LLM Provider & Model

| Agent / Node | Provider | Model ID | Rationale |
|-------------|----------|----------|-----------|
| `generate_sql` | Gemini | `gemini-2.5-flash` | Fast, cheap, strong at structured SQL from a compact schema prompt. |
| `narrate` | Gemini | `gemini-2.5-flash` | Short narrative over a tiny result preview; flash is ample and cheap. |

Provider is auto-detected from `AGENT_GEMINI_API_KEY` via the existing `LLMClient`. Model overridable with `AGENT_LLM_MODEL`.

**Fallback behaviour:** On Gemini error/timeout/rate-limit, the node retries up to 2× with exponential back-off (handled in/around the LLM call); if still failing it sets `state["error"]`, the graph routes to `handle_error`, the audit row is marked `failed`, and the API returns 502 with a clear message. This is production resilience, not a test stub — tests call the real Gemini API with the `.env` key.

**Prompt strategy:** System/user split. `generate_sql` system prompt (`src/prompts/generate_sql.md`) instructs: emit exactly one read-only DuckDB SELECT over the given table, using only the listed columns, returning raw SQL with no prose/markdown fences. User content = compact schema block (table name, columns+types, ≤`AGENT_MAX_SAMPLE_ROWS` sample rows, basic aggregates) + the NL question. `narrate` (`src/prompts/narrate.md`) gets the question, the SQL, and a capped result preview and returns a 2–4 sentence senior-analyst narrative. Output parsing is defensive: strip code fences; reject non-SELECT.

---

## Tools & Tool Calling

| Tool name | Description | Inputs | Output | Side-effects |
|-----------|-------------|--------|--------|--------------|
| `duckdb_execute` | Run a read-only SQL statement on the dataset's DuckDB table | `sql: str`, `duckdb_path: str` | `columns: list[str]`, `rows: list[list]` (capped), `row_count: int`, `duration_ms: int` | Reads DuckDB; no writes |
| `schema_profile` | Build the token-economical schema context for a dataset | `dataset_id`, `duckdb_path`, `max_sample_rows` | `SchemaContext` (columns, types, samples, aggregates) | Reads DuckDB |

**Tool selection strategy:** Rule-based — the chain calls each tool at a fixed step; the LLM does not choose tools. `generate_sql` produces SQL (no tool); `execute_sql` always calls `duckdb_execute`.

**Tool failure handling:** `duckdb_execute` failure (bad SQL, missing column) is caught by `execute_sql`, which sets `state["error"]` → `handle_error`. No retry on SQL errors (a malformed query won't fix itself); LLM-call retries are handled at the LLM layer.

---

## Agent State

```python
class AgentState(TypedDict, total=False):
    # Identity
    run_id: str                       # set by runner (AuditLog row id)
    session_id: str                   # active session, set by runner
    dataset_id: str                   # target dataset, set by runner

    # Input
    nl_question: str                  # the user's natural-language question
    duckdb_path: str                  # set by runner from settings
    max_sample_rows: int              # token-economy cap, set by runner from settings

    # Pipeline data (populated progressively)
    table_name: str                   # DuckDB table for the dataset (profile_schema)
    schema_context: dict              # columns/types/samples/aggregates (profile_schema)
    generated_sql: str                # SQL from the LLM (generate_sql)
    result_columns: list[str]         # execute_sql
    result_rows: list[list]           # capped result rows (execute_sql)
    row_count: int                    # full result row count (execute_sql)
    duration_ms: int                  # query execution time (execute_sql)

    # Output
    narrative: str                    # senior-analyst narrative (narrate)
    status: str                       # "completed" | "failed" (finalize/handle_error)

    # Control
    error: str | None                 # set by any node on fatal failure
```

---

## Nodes / Steps

### `profile_schema`
**Reads from state:** `dataset_id`, `duckdb_path`, `max_sample_rows`
**Writes to state:** `table_name`, `schema_context` (or `error`)
**LLM call:** No.
**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| DuckDB | Read column metadata + up to `max_sample_rows` sample rows + basic aggregates | fatal (set `error`) |

**Behaviour:** Builds the compact, token-economical context. This node is the enforcement point for the token-economy constraint: it caps sample rows at `max_sample_rows` and never materializes the full table into state or the prompt.

### `generate_sql`
**Reads from state:** `schema_context`, `nl_question`, `table_name`
**Writes to state:** `generated_sql` (or `error`)
**LLM call:** Yes — Gemini `gemini-2.5-flash`, system prompt `generate_sql.md`, output = raw SQL.
**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini | Generate one read-only SELECT | retry 2× then fatal (set `error`) |

**Behaviour:** Produces a single read-only SELECT. Strips code fences; validates it is a SELECT and references only known columns/table; rejects anything else (set `error`).

### `execute_sql`
**Reads from state:** `generated_sql`, `duckdb_path`
**Writes to state:** `result_columns`, `result_rows` (capped), `row_count`, `duration_ms` (or `error`)
**LLM call:** No.
**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| DuckDB | Execute SELECT, capture rows/count/timing | fatal (set `error`) |

**Behaviour:** Runs the SQL on DuckDB, times it, truncates returned rows to the display cap for the UI while recording the true `row_count`.

### `narrate`
**Reads from state:** `nl_question`, `generated_sql`, `result_columns`, `result_rows` (capped preview)
**Writes to state:** `narrative` (or `error`)
**LLM call:** Yes — Gemini `gemini-2.5-flash`, system prompt `narrate.md`.
**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini | Produce 2–4 sentence narrative | retry 2× then fatal (set `error`) |

**Behaviour:** Interprets the result like a senior analyst. Receives only the capped preview, never the full result set.

### `finalize`
**Reads:** all output fields. **Writes:** `status="completed"`. No external calls.

### `handle_error`
**Reads:** `error`, `run_id`. **Writes:** `status="failed"`. The runner persists the failure to the audit row.

---

## Graph / Flow Topology

```
START
  │
  ▼
profile_schema ──(error)──► handle_error ──► END
  │
  ▼
generate_sql ──(error)──► handle_error
  │
  ▼
execute_sql ──(error)──► handle_error
  │
  ▼
narrate ──(error)──► handle_error
  │
  ▼
finalize ──► END
```

**Conditional edges:**

| Source node | Condition | Target |
|-------------|-----------|--------|
| `profile_schema` | `state["error"]` set | `handle_error` |
| `profile_schema` | else | `generate_sql` |
| `generate_sql` | `state["error"]` set | `handle_error` |
| `generate_sql` | else | `execute_sql` |
| `execute_sql` | `state["error"]` set | `handle_error` |
| `execute_sql` | else | `narrate` |
| `narrate` | `state["error"]` set | `handle_error` |
| `narrate` | else | `finalize` |

**Phase-3 expansion (noted, not built in Phase 1):** a `clarify` node before `generate_sql` (HITL checkpoint, routes back to the user when confidence is low) and a `recommend` node after `narrate`. **Phase-2:** a `propose_chart` node after `narrate`. **Phase-4:** `profile_schema` accepts multiple datasets and `generate_sql` emits multi-table SQL.

---

## Memory & Context

| Scope | Mechanism | What is stored |
|-------|-----------|----------------|
| **Within a run** | LangGraph state | schema context, SQL, capped result, narrative |
| **Across runs** | SQLAlchemy (metadata) + DuckDB (data) | sessions, datasets, full audit trail; dataset rows in DuckDB |
| **Conversation** | none in Phase 1 | (multi-turn clarify is Phase 3) |

**Context window management:** Enforced upstream — `profile_schema` caps sample rows at `AGENT_MAX_SAMPLE_ROWS` and `narrate` sees only a capped result preview, so prompts stay small regardless of dataset size.

---

## Human-in-the-Loop Checkpoints

None in Phase 1 (the chain runs end-to-end). The Phase-3 `clarify` node introduces the only HITL checkpoint: when SQL-generation confidence is low, the agent returns a clarifying question instead of an answer and waits for the user's reply.

---

## Error Handling & Recovery

**Node-level:** Each node wraps its work in try/except; on a fatal error it returns `{**state, "error": str(exc)}`.

**Graph-level (`handle_error` node):**
- Reads: `state["error"]`, `state["run_id"]`
- Sets `status="failed"`; the runner updates the audit row (`status="failed"`, `error_message`, `duration_ms`) and the API returns 502 (LLM) or 400/500 (DuckDB/SQL).
- Logs the error with `run_id` context; terminates the graph.

**Resume / retry strategy:** No graph-level checkpointing in Phase 1; a failed ask is simply re-asked. LLM calls retry internally (2× back-off).

**Partial failure:** None — the chain is all-or-nothing for a single answer; a failed run yields a clear error and an audit row, never partial fake output.

---

## Observability

| Signal | What | Where |
|--------|------|-------|
| **Trace** | One audit row per ask, with timing | SQLite `audit_logs` |
| **LLM calls** | Node name, model, latency, success/error | structured log (structlog) |
| **Tool calls** | `duckdb_execute` SQL, row count, duration | structured log + audit row |
| **Run outcome** | status, duration, error | `audit_logs` + structured log |

---

## Concurrency Model

- **Run isolation:** Each ask is a self-contained graph invocation scoped by `run_id`/`session_id`; DuckDB connections are per-call. Local single-user tool — no global run lock needed.
- **Parallel nodes within a run:** None — the chain is strictly sequential (each node depends on the prior).
- **Checkpointing:** None in Phase 1 (no long-running or HITL flow yet).

---

## Graph Assembly (`src/graph/agent.py`)

```python
graph = StateGraph(AgentState)

graph.add_node("profile_schema", profile_schema)
graph.add_node("generate_sql", generate_sql)
graph.add_node("execute_sql", execute_sql)
graph.add_node("narrate", narrate)
graph.add_node("finalize", finalize)
graph.add_node("handle_error", handle_error)

graph.set_entry_point("profile_schema")

def _route(nxt: str):
    return lambda s: "handle_error" if s.get("error") else nxt

graph.add_conditional_edges("profile_schema", _route("generate_sql"),
                            {"generate_sql": "generate_sql", "handle_error": "handle_error"})
graph.add_conditional_edges("generate_sql", _route("execute_sql"),
                            {"execute_sql": "execute_sql", "handle_error": "handle_error"})
graph.add_conditional_edges("execute_sql", _route("narrate"),
                            {"narrate": "narrate", "handle_error": "handle_error"})
graph.add_conditional_edges("narrate", _route("finalize"),
                            {"finalize": "finalize", "handle_error": "handle_error"})

graph.add_edge("finalize", END)
graph.add_edge("handle_error", END)

agentic_ai = graph.compile()
```
