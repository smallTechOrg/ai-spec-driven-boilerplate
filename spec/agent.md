# Agent

> The agent graph for the **Data Analysis** capability. This is the single source of truth for
> graph topology, state shape, and the local-compute / LLM-plan loop. It REPLACES the bare
> `transform_text` capability slot. The reusable seam nodes (`guard_input`, `handle_error`,
> `finalize`) from the baseline are kept; `load_memory`/`write_memory` stay dormant in Phase 1
> and are wired in Phase 2.

## Pattern

**LLM-plan → local-execute → LLM-explain, with a bounded code-repair loop.** This is a
constrained ReAct: the only "tool" the model drives is a single **local pandas execution**
step. The LLM never sees the full data; it sees schema + a bounded sample and proposes code.
The code runs locally; its numeric result (not the data) is fed back for explanation. (See
`harness/patterns/agentic-ai.md` — plan/act/observe with a single deterministic local tool.)

## Why this shape

- **Data locality:** only `load_dataset` touches the full data, and it is a LOCAL node. The two
  LLM nodes (`propose_code`, `explain_result`) receive only schema+sample and numbers.
- **Auditability:** `execute_code` captures the exact code string and its result into state and
  thence into the DB and the response.
- **Robustness:** a bounded repair loop lets the LLM fix code that errors once, without
  unbounded looping (reuses the existing `react_max_steps` budget cap).

## State shape (`src/graph/state.py` — analysis fields added to `AgentState`)

```python
class AgentState(TypedDict, total=False):
    # Identity
    run_id: str
    dataset_id: str            # which uploaded dataset to analyse
    conversation_id: str       # = dataset_id from Phase 2 (session memory key); blank in P1

    # Input
    question: str              # the user's natural-language question

    # Dataset (LOCAL — full df never leaves the box)
    df_path: str               # local path data/uploads/<dataset_id>.csv
    schema: list[dict]         # [{name, dtype}] derived locally
    sample: dict               # {preview_rows: [...], summary: {col: {...}}} — bounded
    row_count: int

    # Plan/execute/explain
    proposed_code: str         # the pandas snippet the LLM proposed (assigns `result`)
    code_result: object        # JSON-serializable value captured from the sandbox
    exec_error: str | None     # structured sandbox error (drives the repair loop)
    repair_attempts: int       # bounded by react_max_steps
    explanation: str           # plain-language explanation of code_result

    # Output (assembled in finalize)
    answer: str                # human-readable numeric answer string
    code: str                  # = proposed_code that actually produced the result

    # Memory (dormant P1, active P2)
    memory_context: str

    # Observability — populated progressively
    tokens_in: int
    tokens_out: int
    cost_usd: float
    model: str
    node_trace: list[NodeTrace]

    # Control
    error: str | None          # fatal, human-readable
    guard_code: str | None
    status: str
```

## Nodes

| Node | Kind | Reads | Writes | Sends to LLM |
|------|------|-------|--------|--------------|
| `guard_input` | seam (reused) | `question` | `error`/`guard_code` on bad input | — |
| `load_dataset` | LOCAL | `dataset_id` | `df_path`, `schema`, `sample`, `row_count` | nothing |
| `propose_code` | LLM | `schema`, `sample`, `question`, `exec_error?`, `memory_context?` | `proposed_code` | **schema + bounded sample + question only** |
| `execute_code` | LOCAL sandbox | `df_path`, `proposed_code` | `code_result` or `exec_error` | nothing |
| `explain_result` | LLM | `question`, `code_result` | `explanation` | **the question + the numeric result only** |
| `finalize` | seam (reused) | all | `answer`, `code`, `status="completed"`; persist `QueryRow` | — |
| `handle_error` | seam (reused) | `error`/`exec_error` | `status="failed"`, human-readable error | — |
| (`load_memory`/`write_memory`) | seam (dormant P1) | `conversation_id` | `memory_context` / persists turns | — |

### `load_dataset` (LOCAL)
Loads `data/uploads/<dataset_id>.csv` via `src/tools/dataset.py` into a DataFrame, derives the
schema and the bounded sample/summary (first `sample_rows` rows + per-column stats), and writes
them to state. The DataFrame itself is NOT stored in state long-term; `execute_code` reloads it
from `df_path` for execution. On a missing/corrupt file → set `error` → `handle_error`.
Emits `dataset.loaded` log (row_count, n_cols).

### `propose_code` (LLM — schema+sample only)
Builds a prompt from `src/prompts/transform.md` (the analysis system prompt) + the schema +
the bounded sample + the question (+ `memory_context` from Phase 2, + the prior `exec_error` on
a repair pass). Calls Gemini via `LLMClient().call_model(...)` routed through `route("tools")`.
Parses out a single pandas snippet that assigns to `result`. Writes `proposed_code`. Accumulates
tokens/cost. Emits `code.proposed` log. The **full dataset is never included** — only
`schema` + `sample`.

### `execute_code` (LOCAL sandbox)
Calls `src/tools/sandbox.run(code, df)` (reloading `df` from `df_path`). The sandbox `exec`s the
code in a restricted namespace (`df`, `pd`, safe builtins only) under a wall-clock timeout, and
returns either `result` (JSON-coerced) or a structured error. On success → write `code_result`,
clear `exec_error`. On error → write `exec_error`, increment `repair_attempts`. Emits
`code.executed` log (ok/err, duration_ms).

### `explain_result` (LLM — numbers only)
Sends the question + the captured `code_result` (numbers only — NOT the dataframe) to Gemini for
a short plain-language explanation. Writes `explanation`. Accumulates tokens/cost. Emits
`result.explained` log.

### `finalize` (seam, reused)
Assembles `answer` (a readable string from `code_result`), sets `code = proposed_code`, persists
a `QueryRow` (question, code, result_json, explanation, tokens, cost, latency, model, status),
sets `status="completed"`. Emits `run.complete`.

### `handle_error` (seam, reused)
Sets `status="failed"` and ensures a human-readable `error` (bad CSV / repair budget exhausted /
LLM failure). No stack traces to the user. Emits `run.failed`.

## Edges

```
START
  └─> guard_input
        ├─ error?        ─> handle_error
        └─ ok            ─> load_dataset
load_dataset
        ├─ load error?   ─> handle_error
        └─ ok            ─> propose_code
propose_code
        ├─ LLM error?    ─> handle_error
        └─ ok            ─> execute_code
execute_code            (conditional: after_execute)
        ├─ ok            ─> explain_result
        ├─ exec_error & repair_attempts < react_max_steps ─> propose_code   (repair loop)
        └─ exec_error & budget exhausted                  ─> handle_error
explain_result
        ├─ LLM error?    ─> handle_error
        └─ ok            ─> finalize
finalize     ─> END
handle_error ─> END
```

`after_execute(state)` (in `src/graph/edges.py`):
```python
def after_execute(state):
    if state.get("error"):
        return "handle_error"
    if state.get("exec_error"):
        if state.get("repair_attempts", 0) < get_settings().react_max_steps:
            return "propose_code"          # feed the error back for one repair
        return "handle_error"              # budget exhausted → graceful failure
    return "explain_result"
```

## Graph assembly (`src/graph/agent.py`)

```python
def _build_graph() -> StateGraph:
    g = StateGraph(AgentState)
    g.add_node("guard_input", guard_input)
    g.add_node("load_dataset", load_dataset)
    g.add_node("propose_code", propose_code)
    g.add_node("execute_code", execute_code)
    g.add_node("explain_result", explain_result)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)

    g.set_entry_point("guard_input")
    g.add_conditional_edges("guard_input",
        lambda s: "handle_error" if s.get("error") else "load_dataset",
        {"handle_error": "handle_error", "load_dataset": "load_dataset"})
    g.add_conditional_edges("load_dataset",
        lambda s: "handle_error" if s.get("error") else "propose_code",
        {"handle_error": "handle_error", "propose_code": "propose_code"})
    g.add_conditional_edges("propose_code",
        lambda s: "handle_error" if s.get("error") else "execute_code",
        {"handle_error": "handle_error", "execute_code": "execute_code"})
    g.add_conditional_edges("execute_code", after_execute,
        {"propose_code": "propose_code", "explain_result": "explain_result",
         "handle_error": "handle_error"})
    g.add_conditional_edges("explain_result",
        lambda s: "handle_error" if s.get("error") else "finalize",
        {"handle_error": "handle_error", "finalize": "finalize"})
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    return g.compile()
```

> Phase 2 inserts `load_memory` (after `guard_input`, before `load_dataset`) and `write_memory`
> (between `explain_result` and `finalize`), keyed by `conversation_id = dataset_id`.

## Concurrency

- Within one query the graph is **sequential** (each node depends on the prior). The repair
  loop is the only cycle and is hard-bounded by `react_max_steps`.
- The FastAPI process handles concurrent queries across requests; each invocation owns its own
  `AgentState` and reloads its own DataFrame — no shared mutable dataframe state.

## Error handling

| Failure | Detected in | Result to user |
|---------|-------------|----------------|
| Empty/oversized/non-CSV upload | upload endpoint / `load_dataset` | "Could not read this file as a CSV…" |
| Off-topic / empty question | `guard_input` | "Please ask a question about the data." |
| LLM API error/timeout | `propose_code` / `explain_result` | "The analysis service is unavailable, please retry." |
| Proposed code errors once | `execute_code` → repair loop | (auto-repair; user sees nothing) |
| Proposed code errors past budget | `after_execute` → `handle_error` | "Could not compute an answer for this question." |
| Sandbox timeout | `execute_code` | treated as exec_error → repair, then graceful failure |

Every LLM and sandbox call is wrapped in try/except with a timeout; a failure sets a
human-readable `error` and routes to `handle_error`, never a crash or stack trace to the UI.

## What is sent to the LLM (the data-locality contract, restated)

- `propose_code`: system prompt + **schema** + **bounded sample/summary** + the **question**
  (+ prior `exec_error` on repair, + `memory_context` from Phase 2). **Never the full df.**
- `explain_result`: the **question** + the **numeric `code_result`**. **Never the full df.**
- The full DataFrame is read and computed over **only** inside the LOCAL `execute_code` sandbox.
