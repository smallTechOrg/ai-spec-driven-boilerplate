# Agent

The DataChat agent graph (LangGraph). It turns a plain-English question over a local dataset into a plain-English answer + chart, while enforcing — in code — that only schema + aggregates ever reach the LLM.

---

## Agent Architecture Pattern

| Pattern | Use when |
|---------|----------|
| **Single-agent loop** | One LLM drives a deterministic tool-call loop. No branches, no handoffs. |
| **Graph (LangGraph)** | Multi-step pipeline with conditional edges, checkpointing, or parallel nodes. |
| **Multi-agent** | Specialised sub-agents with distinct roles; orchestrator routes between them. |
| **Supervisor** | One supervisor LLM dispatches to worker agents based on task type. |
| **Human-in-the-loop** | Execution pauses at defined checkpoints for user review or approval. |

**Chosen:** **Graph (LangGraph)** running a constrained **ReAct-style reason→act→observe** loop with a hard separation between **LLM reasoning** (over schema/aggregates) and **local tool execution** (over rows). Base composition: **Tool Use (#5)** + **Reasoning/ReAct (#17)** + **Guardrails (#18)** + **Observability (#19)**. The graph is the right floor because the flow has a real branch (compute succeeds vs. fails) and a privacy chokepoint that must sit between reasoning and execution. Phase 4 reaches up to **Memory (#8)**, **Reflection (#4)**, and **Exception Handling (#12)**; Phase 5 adds an **anomaly branch (Routing #2)**. We deliberately stay frugal — at most two LLM calls per question (plan + phrase), targeting one where the question is trivially mappable.

---

## LLM Provider & Model

| Agent / Node | Provider | Model ID | Rationale |
|-------------|----------|----------|-----------|
| `plan_compute` | Gemini | `gemini-2.5-flash` | Cheap, fast structured-plan generation over a tiny schema prompt |
| `phrase_answer` | Gemini | `gemini-2.5-flash` | Cheap phrasing + chart-type choice over a tiny aggregate result |

Single model everywhere to keep cost low (the brief's dealbreaker). `GeminiProvider.DEFAULT_MODEL` is set to `gemini-2.5-flash`; provider auto-detected from `AGENT_GEMINI_API_KEY`.

**Fallback behaviour:** Phase 1 surfaces an LLM error as `api_error("LLM_UNAVAILABLE", ...)`. Phase 4 adds retry/backoff + timeout in `LLMClient`/nodes and a degraded message (the local aggregate result is still returned even if phrasing fails). Not a test stub — tests call real Gemini via `.env`.

**Prompt strategy:** System/user split. `plan_compute` uses a system prompt (`src/prompts/plan.md`) instructing structured JSON output: `{group_by, metric_column, aggregation, filter?}`. `phrase_answer` (`src/prompts/answer.md`) takes the question + aggregate JSON and returns `{answer, chart: {type, x, series}}`. Outputs are parsed and validated (guardrail) before use.

---

## Tools & Tool Calling

| Tool name | Description | Inputs | Output | Side-effects |
|-----------|-------------|--------|--------|--------------|
| `load_dataset` | Ingest a CSV into the local DuckDB working store | file path, dataset_id | local table handle | writes DuckDB local store |
| `build_schema_summary` | Profile schema + column-level scalar aggregates (NO rows) | dataset_id | schema summary (cols, types, row count, min/max/distinct/null) | none |
| `run_aggregation` | Execute the compute plan locally over the FULL dataset | plan, dataset_id | bounded aggregate result table | reads DuckDB local store |
| `assert_no_raw_rows` | Guard: reject any LLM-bound payload that isn't schema/aggregate-shaped | payload | payload or raises | none (raises on violation) |

**Tool selection strategy:** Deterministic graph order, not free LLM choice — `build_schema_summary` → (LLM plans) → `run_aggregation` → (LLM phrases). The LLM chooses *what to aggregate*, never *whether to touch rows*; row access is restricted to local tools.

**Tool failure handling:** Each tool raises on failure; the node catches, sets `state["error"]`, and routes to `handle_error`. Phase 4 adds a single re-plan retry when `run_aggregation` rejects an invalid plan.

---

## Privacy Boundary Enforcement

This is the heart of the product, enforced in the graph:

- **Only two nodes call the LLM:** `plan_compute` and `phrase_answer`. No other node may import or call `LLMClient`.
- `plan_compute`'s outgoing payload = `build_schema_summary(...)` output only (schema + scalar aggregates). It calls `assert_no_raw_rows(payload)` immediately before `LLMClient().call_model(...)`.
- `phrase_answer`'s outgoing payload = `run_aggregation(...)` output only (a small grouped result). It calls `assert_no_raw_rows(payload)` immediately before the LLM call.
- `assert_no_raw_rows` (in `src/tools/compute.py`) enforces the contract: the payload must be a schema summary or an aggregate result under a bounded row count (e.g. ≤ N grouped rows) and must not contain a raw-row marker. It raises if violated.
- **Row access is confined to `src/tools/` (DuckDB/pandas).** Nodes never hold raw rows in state that crosses to the LLM; `execute_local` keeps the full data inside DuckDB and emits only the aggregate.

Proven by `tests/phase1/test_privacy_boundary.py` (spies on the LLM payload with a sentinel-row fixture and asserts no raw cell value appears).

---

## Agent State

```python
class AgentState(TypedDict, total=False):
    # Identity
    run_id: str                          # set by runner at init

    # Input
    dataset_id: str                      # which local dataset/connection to query
    question: str                        # the user's plain-English question
    messages: list                       # chat-turn history (Phase 4 memory)

    # Pipeline data (populated progressively; NONE of the LLM-bound fields hold raw rows)
    schema_summary: dict                 # set by profile_data (cols/types/scalar aggregates)
    compute_plan: dict                   # set by plan_compute (group_by/metric/aggregation)
    aggregate_result: dict               # set by execute_local (bounded grouped result)

    # Output
    answer_text: str                     # set by phrase_answer
    chart_spec: dict                     # set by phrase_answer ({type, x, series})
    status: str                          # "completed" | "failed"

    # Control
    error: str | None                    # set by any node on fatal failure
```

---

## Nodes / Steps

### `profile_data`
**Reads from state:** `dataset_id`
**Writes to state:** `schema_summary`
**LLM call:** no.
**External calls:** DuckDB read (local) — on failure: fatal (set `error`).
**Behaviour:** Calls `build_schema_summary(dataset_id)` to produce schema + scalar aggregates. No rows. Pure local profiling.

### `plan_compute`
**Reads from state:** `schema_summary`, `question`, `messages`
**Writes to state:** `compute_plan`
**LLM call:** yes — Gemini `gemini-2.5-flash`, system `prompts/plan.md`, structured JSON plan. Payload = schema summary + question only; `assert_no_raw_rows` called before the call.
**External calls:** Gemini — on failure: fatal (`LLM_UNAVAILABLE`).
**Behaviour:** Asks the model which columns to group by / aggregate. Parses + validates the JSON plan (guardrail). Invalid → `error` (Phase 4: re-plan once).

### `execute_local`
**Reads from state:** `compute_plan`, `dataset_id`
**Writes to state:** `aggregate_result`
**LLM call:** no.
**External calls:** DuckDB (local) over the FULL dataset — on failure: fatal (`COMPUTE_FAILED`).
**Behaviour:** Validates the plan's columns against the schema, runs `run_aggregation(...)` locally over all rows, returns a bounded aggregate result. The privacy boundary's local side.

### `phrase_answer`
**Reads from state:** `question`, `aggregate_result`
**Writes to state:** `answer_text`, `chart_spec`
**LLM call:** yes — Gemini `gemini-2.5-flash`, system `prompts/answer.md`. Payload = question + aggregate result only; `assert_no_raw_rows` called before the call.
**External calls:** Gemini — on failure: fatal (Phase 4: degraded — return the raw aggregate without prose).
**Behaviour:** Turns the aggregate into a plain-English answer and a chart spec (type chosen from the data shape).

### `finalize`
**Reads from state:** `answer_text`, `chart_spec`, `run_id`
**Writes to state:** `status="completed"`
**Behaviour:** Persists the `Question` row (answer + chart spec) to SQLite.

### `handle_error`
**Reads from state:** `error`, `run_id`
**Writes to state:** `status="failed"`
**Behaviour:** Persists failure (status + error_message) and terminates.

---

## Graph / Flow Topology

```
START
  │
  ▼
profile_data ──(error)──► handle_error ──► END
  │
  ▼
plan_compute ──(error)──► handle_error
  │
  ▼
execute_local ──(error)──► handle_error
  │
  ▼
phrase_answer ──(error)──► handle_error
  │
  ▼
finalize ──► END
```

**Conditional edges:**

| Source node | Condition | Target |
|-------------|-----------|--------|
| `profile_data` | `state["error"]` set | `handle_error` |
| `profile_data` | else | `plan_compute` |
| `plan_compute` | `state["error"]` set | `handle_error` |
| `plan_compute` | else | `execute_local` |
| `execute_local` | `state["error"]` set | `handle_error` |
| `execute_local` | else | `phrase_answer` |
| `phrase_answer` | `state["error"]` set | `handle_error` |
| `phrase_answer` | else | `finalize` |

*(Phase 5 adds an `anomaly` branch off the entry router when the request is an anomaly request.)*

---

## Memory & Context

| Scope | Mechanism | What is stored |
|-------|-----------|----------------|
| **Within a run** | LangGraph state | schema summary, plan, aggregate, answer, chart |
| **Across runs** | SQLite app store | dataset metadata, past questions/answers |
| **Conversation** | `AgentState.messages` + SQLite (Phase 4) | prior turns so follow-ups ("now by month") resolve in context |

**Context window management:** Prompts are tiny by design (schema + small aggregates), so no truncation needed. Conversation memory (Phase 4) keeps a bounded window of recent turns; raw rows are never part of context.

---

## Human-in-the-Loop Checkpoints

None. Read-only personal analysis; no irreversible actions. (Section retained intentionally empty.)

---

## Error Handling & Recovery

**Node-level:** Each node wraps its work in try/except; on failure sets `state["error"]` and routing sends it to `handle_error`.

**Graph-level (`handle_error`):**
- Reads `state.error`, `state.run_id`
- Updates the `Question`/run row: status → "failed", `error_message`, timestamp
- Logs with `run_id` context; terminates the graph

**Resume / retry strategy:** Phase 1 — none (each question is a fresh run). Phase 4 — `plan_compute` re-plans once on a guardrail rejection; `LLMClient` retries with backoff on transient Gemini errors.

**Partial failure:** Phase 4 — if `phrase_answer` fails, return the aggregate result with a generic phrasing (degraded, not crashed). Local compute failures remain fatal (no meaningful answer possible).

---

## Observability

| Signal | What | Where |
|--------|------|-------|
| **Trace** | One trace per run, one span per node | structured stdout log (structlog) |
| **LLM calls** | model, prompt/response sizes, latency, call count per question | structured log |
| **Tool calls** | tool name, success/error, latency, rows-scanned (local) | structured log |
| **Run outcome** | status, duration, error if any | SQLite + structured log |
| **Privacy assertion** | each `assert_no_raw_rows` pass logged (boundary upheld) | structured log |

---

## Concurrency Model

- **Run isolation:** one question = one run scoped by `run_id`; the personal single-user tool serves requests sequentially per process. No cross-run shared mutable state.
- **Parallel nodes within a run:** none — the pipeline is strictly ordered (profile → plan → execute → phrase).
- **Checkpointing:** none in Phase 1 (runs are short). Phase 4 conversation memory persists turns to SQLite, not a LangGraph checkpointer.

---

## Graph Assembly (`src/graph/agent.py`)

```python
from langgraph.graph import StateGraph, END
from graph.state import AgentState
from graph.nodes import (
    profile_data, plan_compute, execute_local,
    phrase_answer, finalize, handle_error,
)
from graph.edges import (
    after_profile, after_plan, after_execute, after_phrase,
)

def _build_graph() -> StateGraph:
    g = StateGraph(AgentState)
    g.add_node("profile_data", profile_data)
    g.add_node("plan_compute", plan_compute)
    g.add_node("execute_local", execute_local)
    g.add_node("phrase_answer", phrase_answer)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)

    g.set_entry_point("profile_data")
    g.add_conditional_edges("profile_data", after_profile,
        {"plan_compute": "plan_compute", "handle_error": "handle_error"})
    g.add_conditional_edges("plan_compute", after_plan,
        {"execute_local": "execute_local", "handle_error": "handle_error"})
    g.add_conditional_edges("execute_local", after_execute,
        {"phrase_answer": "phrase_answer", "handle_error": "handle_error"})
    g.add_conditional_edges("phrase_answer", after_phrase,
        {"finalize": "finalize", "handle_error": "handle_error"})
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    return g.compile()

agentic_ai = _build_graph()
```
