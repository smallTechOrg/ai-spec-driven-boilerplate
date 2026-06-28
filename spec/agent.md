# Agent

The PLAN-THEN-EXECUTE LangGraph for the Local Data Analyst. **The full graph spine and the privacy boundary are REAL in Phase 1.** Later-phase nodes (clarify, auto-pick-file) are added around this spine; Phase 1 wires the complete plan → execute → aggregate → narrate → suggest path.

---

## Agent Architecture Pattern

| Pattern | Use when |
|---------|----------|
| **Single-agent loop** | One LLM drives a deterministic tool-call loop. No branches, no handoffs. |
| **Graph (LangGraph)** | Multi-step pipeline with conditional edges, checkpointing, or parallel nodes. |
| **Multi-agent** | Specialised sub-agents with distinct roles; orchestrator routes between them. |
| **Supervisor** | One supervisor LLM dispatches to worker agents based on task type. |
| **Human-in-the-loop** | Execution pauses at defined checkpoints for user review or approval. |

**Chosen:** **Graph (LangGraph) — PLAN-THEN-EXECUTE.** The LLM first drafts a plan + the SQL to run (it never sees data), the SQL runs **locally** in DuckDB, results are reduced to aggregates, and only those aggregates are narrated by the LLM. This split is exactly what lets the privacy boundary be enforced structurally: planning and narration are LLM nodes that receive schema + aggregates only, while the execute node is a pure local node that touches the raw data. A linear loop could not guarantee that raw rows never reach a prompt; the explicit graph makes the boundary a property of the topology.

---

## LLM Provider & Model

| Agent / Node | Provider | Model ID | Rationale |
|-------------|----------|----------|-----------|
| `plan` (draft plan + DuckDB SQL) | Gemini | `gemini-2.5-flash` | Low cost tier; flash is fast and strong enough for SQL drafting against a known schema. |
| `narrate` (answer + key stats + chart spec + summary table + insight) | Gemini | `gemini-2.5-flash` | Narration of aggregate numbers; flash keeps per-query cost and latency low. |
| `suggest_follow_ups` (2–3 follow-ups) | Gemini | `gemini-2.5-flash` | Cheap, short generation. |
| `clarify` (Phase 4) | Gemini | `gemini-2.5-flash` | Ambiguity check; same cost tier. |
| `auto_pick_dataset` (Phase 3) | Gemini | `gemini-2.5-flash` | Choose dataset(s) from schemas only. |

The model is read from settings (`AGENT_LLM_MODEL`, default `gemini-2.5-flash`); the provider default in `src/llm/providers/gemini.py` is changed from `gemini-2.5-pro` to `gemini-2.5-flash`. **No Anthropic** (key empty).

**Fallback behaviour:** retry with exponential backoff on transient Gemini errors (rate-limit / 5xx); after retries exhausted the node sets `state["error"]` and routes to `handle_error`, which records the failure and the API surfaces it. Tests call the real Gemini API with keys from `.env` — there is no offline/stubbed LLM path.

**Prompt strategy:** system/user split. System prompts live in `src/prompts/*.md` (`plan.md`, `narrate.md`, `follow_ups.md`; later `clarify.md`, `select_dataset.md`). Structured output via JSON: the `plan` node asks for `{ "steps": [...], "sql": "..." }`; the `narrate` node asks for `{ "answer", "key_stats", "chart_spec", "summary_table", "insight" }`; parsed and validated against pydantic models before use. Prompts include only schema (column names/types) + profile/aggregate numbers — never raw rows.

---

## Tools & Tool Calling

| Tool name | Description | Inputs | Output | Side-effects |
|-----------|-------------|--------|--------|--------------|
| `duckdb_query` | Pure, LOCAL DuckDB query runner. Executes generated SQL against the dataset's DuckDB table(s). | `sql: str`, `dataset_id: str` | result rows (list of dicts) + column metadata — **stays local** | None remote; reads local DuckDB only |
| `profile_dataset` | Computes the data profile via local DuckDB queries. | `dataset_id: str` | profile dict (rows, columns+types, null counts, basic stats) | None remote; reads local DuckDB only |
| `aggregate_result` | Reduces raw query rows to summary numbers / a small aggregate table fit for narration. | raw rows + intent | aggregates dict (the ONLY data allowed past the boundary) | None |
| `estimate_cost` | Converts prompt/completion token counts to estimated USD at the flash price. | token counts | `est_usd: float` | None |

**Tool selection strategy:** deterministic — the graph topology fixes the order. The LLM does not free-choose tools; it produces SQL in the `plan` node, which the `local_execute` node runs via `duckdb_query`. This is what makes the privacy boundary auditable.

**Tool failure handling:** `duckdb_query` errors (bad SQL, type error) are caught by the `local_execute` node, which sets `state["error"]` with the attempted SQL preserved so the user always sees what was tried; routes to `handle_error`. `profile_dataset` errors fail the upload with `api_error`.

---

## Agent State

```python
from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # Identity
    run_id: str                          # set at initialisation
    dataset_id: str                      # the dataset being queried

    # Input
    question: str                        # the user's plain-English question
    messages: list[dict]                 # prior conversation turns [{role, content}, ...]

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
    error: str | None                    # set by any node on fatal failure
    checkpoint: str | None               # last completed node (for resume)
```

---

## Nodes / Steps

### `profile`
**Reads from state:** `dataset_id`
**Writes to state:** `schema`, `profile`
**LLM call:** no.
**External calls:**
| System | Operation | On Failure |
|--------|-----------|------------|
| DuckDB (local) | profile queries (count, types, nulls, stats) | fatal (set `error`) |

**Behaviour:** loads the dataset's schema and computes the profile via local DuckDB queries. In the ask flow the profile is usually already cached on the `Dataset` row from upload-time auto-profiling; this node guarantees `schema`/`profile` are populated before planning. Auto-profiling on upload is the same `profile_dataset` tool invoked at ingest time.

### `plan` (LLM)
**Reads from state:** `question`, `schema`, `profile`, `messages`
**Writes to state:** `plan_steps`, `generated_sql`, token counts
**LLM call:** yes — system prompt `prompts/plan.md`; model `gemini-2.5-flash`; output JSON `{steps, sql}`. **Receives schema + profile only — NO raw rows.**
**External calls:**
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini | draft plan + SQL | retry/backoff → fatal (set `error`) |

**Behaviour:** turns the question + schema/profile into a multi-step plan and a single DuckDB SQL query (aggregating where appropriate). Validates the returned JSON against a pydantic model. The SQL is constrained to read-only `SELECT` (no DDL/DML); the execute node enforces this.

### `local_execute`
**Reads from state:** `generated_sql`, `dataset_id`
**Writes to state:** `query_rows`, `query_columns`
**LLM call:** no.
**External calls:**
| System | Operation | On Failure |
|--------|-----------|------------|
| DuckDB (local) | run `generated_sql` via `duckdb_query` | fatal (set `error`, preserve attempted SQL) |

**Behaviour:** runs the generated SQL locally. Rejects non-`SELECT` statements. The raw result rows stay in `query_rows` and are **never** written into any prompt. This is the node that touches raw data; it has no LLM call.

### `aggregate`
**Reads from state:** `query_rows`, `query_columns`
**Writes to state:** `aggregates`
**LLM call:** no.
**External calls:** none.
**Behaviour:** reduces raw rows to summary numbers and a small aggregate table (caps row count, e.g. top-N) suitable for narration. **This node is the privacy gate: only its output (`aggregates`) — plus `schema` — is passed to the narrate node.** If the query already returned an aggregate (e.g. `GROUP BY` totals), this is largely pass-through with a size cap; if it returned many rows, it summarizes them.

### `narrate` (LLM)
**Reads from state:** `question`, `schema`, `aggregates`
**Writes to state:** `answer`, `key_stats`, `chart_spec`, `summary_table`, `insight`, token counts
**LLM call:** yes — system prompt `prompts/narrate.md`; model `gemini-2.5-flash`; output JSON. **Receives schema + aggregates only — NO raw rows.**
**External calls:**
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini | narrate aggregates | retry/backoff → fatal (set `error`) |

**Behaviour:** turns the aggregate numbers into the plain-language answer, key-stat callouts, a declarative `chart_spec` (the node picks the chart type from the aggregate shape), the summary table, and the written insight. Validated against pydantic models.

### `suggest_follow_ups` (LLM)
**Reads from state:** `question`, `schema`, `aggregates`
**Writes to state:** `follow_ups`, token counts
**LLM call:** yes — system prompt `prompts/follow_ups.md`; model `gemini-2.5-flash`. Schema + aggregates only.
**External calls:** Gemini (non-fatal — on failure, `follow_ups = []` and continue; follow-ups are a nicety, not the answer).
**Behaviour:** proposes 2–3 follow-up questions. Degrades gracefully.

### `finalize`
**Reads from state:** all output + cost fields
**Writes to state:** `checkpoint="finalize"`; sets run status via the runner.
**Behaviour:** marks the run complete; the runner persists the full Run audit record (question, plan, generated SQL, aggregates summary, tokens, est_usd) and conversation Messages to SQLite.

### `handle_error`
**Reads from state:** `error`, `run_id`, `generated_sql`
**Writes to state:** `checkpoint="handle_error"`.
**Behaviour:** records the failure; the runner sets the Run status to "failed", stores `error_message` and the attempted SQL so the user sees what was tried. Terminates the graph.

### `clarify` (Phase 4 — thin in Phase 1)
In Phase 1 this node is **not wired** (the graph goes straight from `profile` to `plan`). Phase 4 inserts it before `plan`: if the LLM judges the question ambiguous, it returns a clarifying question and the graph short-circuits to `finalize` with a `needs_clarification` answer; otherwise it proceeds with a best-guess plan and an uncertainty flag.

---

## Graph / Flow Topology

```
START
  │
  ▼
profile ──(error)──► handle_error ──► END
  │
  ▼
plan ──(error)──► handle_error
  │
  ▼
local_execute ──(error)──► handle_error
  │   (raw rows stay here — privacy gate is the next node)
  ▼
aggregate ──(error)──► handle_error
  │   (only aggregates + schema proceed past this point)
  ▼
narrate ──(error)──► handle_error
  │
  ▼
suggest_follow_ups   (non-fatal; on error → empty follow_ups)
  │
  ▼
finalize ──► END
```

**Conditional edges:**

| Source node | Condition | Target |
|-------------|-----------|--------|
| `profile` | `state["error"]` is set | `handle_error`, else `plan` |
| `plan` | `state["error"]` is set | `handle_error`, else `local_execute` |
| `local_execute` | `state["error"]` is set | `handle_error`, else `aggregate` |
| `aggregate` | `state["error"]` is set | `handle_error`, else `narrate` |
| `narrate` | `state["error"]` is set | `handle_error`, else `suggest_follow_ups` |
| `suggest_follow_ups` | (always) | `finalize` |

---

## Privacy Boundary (NON-NEGOTIABLE)

**The LLM (Gemini) receives ONLY two kinds of data: (1) column metadata — `schema` (names + types) and the `profile` (counts, null counts, basic per-column stats); and (2) `aggregates` — summary numbers / small aggregate tables produced by the `aggregate` node. Raw data-row values are NEVER placed in any prompt.**

How it is enforced structurally:
- The only nodes that build LLM prompts are `plan`, `narrate`, and `suggest_follow_ups`. Their prompt builders accept ONLY `schema`/`profile`/`aggregates` — they have no access to `query_rows`.
- `query_rows` (raw result rows) is written only by `local_execute` and read only by `aggregate`. No prompt-building code reads `query_rows`.
- The `local_execute` node (which touches raw data) makes no LLM call. The execute step is local-only by construction.
- The `aggregate` node is the single gate: only its output (`aggregates`), plus `schema`, flows to `narrate`/`suggest_follow_ups`.

How it is tested (REQUIRED — gate test, runs against real Gemini):
- A test loads a dataset whose raw rows contain **distinctive sentinel values** (e.g. a unique string token in a cell) large enough that the answer must come from aggregation, runs a real ask end-to-end, and **captures every prompt string sent to the Gemini provider** (via a spy/recorder on the provider's `call_model`). It asserts that **no sentinel raw-row value appears in any captured prompt** — only schema/column names and aggregate numbers do.
- A second assertion checks that `query_rows` is non-empty (data really was queried locally) while the captured prompts contain none of those row values — proving the boundary, not merely an empty path.
- The fixture must use a dataset large enough that a sampled answer and a full-data answer differ, so the gate proves real aggregation rather than passing on a trivial sample.

---

## Memory & Context

| Scope | Mechanism | What is stored |
|-------|-----------|----------------|
| **Within a run** | LangGraph `AgentState` | All in-progress data (schema, plan, rows, aggregates, narration, cost) |
| **Across runs** | SQLite (Run audit table; Dataset library; DuckDB on-disk per dataset in Phase 2) | Past questions, plans, SQL, result summaries, tokens, cost; the loaded datasets |
| **Conversation** | SQLite `Message` table; threaded into `state["messages"]` | Prior user/assistant turns for the active dataset/session, so follow-ups have context |

**Context window management:** prompts contain only schema + profile + aggregates (all small), so the window is never near its limit. Conversation history is bounded to the recent N turns (sliding window) when threaded into the `plan` prompt. No RAG; no vector store.

---

## Human-in-the-Loop Checkpoints

| Checkpoint | What is shown to the user | Expected user action | Timeout / default |
|------------|--------------------------|----------------------|-------------------|
| Clarification (Phase 4) | A clarifying question when the ask is ambiguous | Answer the clarification, or accept the flagged best-guess | Default: proceed with best-guess + uncertainty flag |

Phase 1 has **no** human-in-the-loop pause — the core path runs straight through.

---

## Error Handling & Recovery

**Node-level:** each node wraps its work in try/except; a fatal failure sets `state["error"]` (preserving any attempted SQL) and the conditional edge routes to `handle_error`. `suggest_follow_ups` is non-fatal (degrades to empty).

**Graph-level (`handle_error` node):**
- Reads: `state.error`, `state.run_id`, `state.generated_sql`
- Updates DB (via the runner): Run status → "failed", `error_message`, the attempted SQL, `updated_at`
- Logs the error with `run_id` context
- Terminates the graph

**Resume / retry strategy:** Phase 1 runs are short and synchronous; a failed run is simply re-asked. `checkpoint` records the last completed node for future resume but is not required in Phase 1. Reproducible re-run (Phase 5) re-executes a stored Run's SQL.

**Partial failure:** follow-up generation failing does not fail the run (empty `follow_ups`). Any failure in plan/execute/aggregate/narrate is fatal but surfaced transparently with what was attempted.

---

## Observability

| Signal | What | Where |
|--------|------|-------|
| **Trace** | One logical run per ask, identified by `run_id` | structlog (stdout JSON) + Run row |
| **LLM calls** | Prompt tokens, completion tokens, model, latency per call | captured from the Gemini response usage metadata; summed into `prompt_tokens`/`completion_tokens`; logged |
| **Cost** | `est_usd` per run = tokens × flash price (via `estimate_cost`) | Run row + API response `cost` field; daily rollup in Phase 5 |
| **Tool calls** | `duckdb_query` SQL, success/error, latency | structured log |
| **Run outcome** | Status, total duration, error + attempted SQL if any | Run row + structured log |

The Gemini provider is extended to return token usage so per-call counts are real (not estimated). `est_usd` uses a configurable flash price-per-1K-tokens constant in `src/data/cost.py`.

---

## Concurrency Model

- **Run isolation:** single user, so runs are effectively serial per dataset. Each run is scoped by `run_id`; the graph is stateless between invocations (state passed in/out), so concurrent asks on different datasets are safe.
- **Parallel nodes within a run:** none in Phase 1 — the plan-then-execute path is inherently sequential (plan depends on profile, execute depends on plan, etc.). `narrate` and `suggest_follow_ups` could parallelise later but are kept sequential for simplicity and to keep cost accounting straightforward.
- **Checkpointing:** none required in Phase 1 (synchronous, short runs). `checkpoint` field reserved for future resume; SqliteSaver may be added if Phase 4 clarification needs a pause.

---

## Graph Assembly (`src/graph/agent.py`)

```python
from langgraph.graph import StateGraph, END

from graph.state import AgentState
from graph.nodes import (
    profile, plan, local_execute, aggregate,
    narrate, suggest_follow_ups, finalize, handle_error,
)
from graph.edges import route_on_error  # returns "handle_error" if state["error"] else the named next node


def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("profile", profile)
    g.add_node("plan", plan)
    g.add_node("local_execute", local_execute)
    g.add_node("aggregate", aggregate)
    g.add_node("narrate", narrate)
    g.add_node("suggest_follow_ups", suggest_follow_ups)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)

    g.set_entry_point("profile")

    g.add_conditional_edges("profile",       lambda s: route_on_error(s, "plan"),          {"plan": "plan", "handle_error": "handle_error"})
    g.add_conditional_edges("plan",          lambda s: route_on_error(s, "local_execute"), {"local_execute": "local_execute", "handle_error": "handle_error"})
    g.add_conditional_edges("local_execute", lambda s: route_on_error(s, "aggregate"),     {"aggregate": "aggregate", "handle_error": "handle_error"})
    g.add_conditional_edges("aggregate",     lambda s: route_on_error(s, "narrate"),       {"narrate": "narrate", "handle_error": "handle_error"})
    g.add_conditional_edges("narrate",       lambda s: route_on_error(s, "suggest_follow_ups"), {"suggest_follow_ups": "suggest_follow_ups", "handle_error": "handle_error"})

    g.add_edge("suggest_follow_ups", "finalize")
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    return g.compile()


agentic_ai = _build_graph()
```

The runner (`src/graph/runner.py`) creates the Run row, builds the initial `AgentState` (`run_id`, `dataset_id`, `question`, `messages`), invokes `agentic_ai`, then persists the audit record (status, plan, SQL, aggregates summary, tokens, est_usd) and conversation Messages.
