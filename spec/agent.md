# Agent — DataChat Analysis Graph

> Required: this project uses LangGraph. This file is the authoritative graph design.

---

## Agent Architecture Pattern

**Chosen:** **Graph (LangGraph)** implementing a **plan-then-execute agentic loop with reflection/self-correction** over **LLM-generated code execution**. Rationale: questions are open-ended (arbitrary analysis over a user dataset), so the agent must generate executable pandas code rather than map onto a fixed op-list (pattern #22, the explicit anti-pattern to avoid). Non-trivial questions need an explicit plan (pattern #6) and a bounded reason→act→observe loop (ReAct, #17) with self-correction on code errors (reflection, #4). The privacy spine forces a hard split between the **LLM-facing nodes** (plan / generate_code / inspect / finalize — see only question + profile + result summaries) and the **local-only execute node** (runs pandas over raw rows, which never reach the LLM).

Patterns by phase:

| Pattern | Phase wired | Where |
|---------|-------------|-------|
| LLM-generated code execution (#22) | P1 | `generate_code` + `execute_local` |
| Planning (#6) | P1 (minimal single-step plan) → P3 (real multi-step plan) | `plan` |
| Tool use / local execution (#5) | P1 | `execute_local` (the "tool" is the local pandas sandbox) |
| ReAct loop (#17) | P1 skeleton (single pass) → P3 (real iterate loop) | `inspect` conditional edge |
| Reflection / self-correction (#4) | P3 | `inspect` → revise `generate_code` on error/bad result |
| Memory (#8) — conversation | P2 | prior-turn summaries threaded into `plan`/`generate_code` |
| Exception handling & recovery (#12) | P1 (handle_error) → P3 (code-error retry) | `handle_error`, `inspect` |
| Guardrails (#18) | P1 | sandboxed executor (whitelist imports, no net/fs); result-size bounds |
| Resource-aware optimization (#16) | P1 (Flash model, cost accounting) → P4 (daily total) | `cost` service |
| Observability (#19) | P1 (code+cost) → P4 (live timeline, streaming) | `run_steps`, structlog |

---

## LLM Provider & Model

| Agent / Node | Provider | Model ID | Rationale |
|-------------|----------|----------|-----------|
| `plan` | Gemini | `gemini-2.5-flash` | Short plan over a known schema; latency-sensitive. |
| `generate_code` | Gemini | `gemini-2.5-flash` | Pandas codegen over a known schema; Flash is sufficient and cheap. |
| `inspect` (P3) | Gemini | `gemini-2.5-flash` | Decide good/retry from result summary or error; escalation to `gemini-2.5-pro` is an env-only change if accuracy demands. |
| `finalize` | Gemini | `gemini-2.5-flash` | Phrase prose answer + (P3) assumptions + follow-ups from result summary. |

All nodes use the single configured provider via `src/llm/client.py` (auto-detected Gemini). Model id is env-configurable (`AGENT_LLM_MODEL`), default `gemini-2.5-flash`.

**Fallback behaviour:** the provider wraps each call with bounded retry + backoff on transient errors (timeout, rate-limit, 5xx). On persistent failure the current node sets `state["error"]` and the graph routes to `handle_error`, which marks the run `failed` with a surfaced message — **never a fabricated answer**. This is production resilience, not a test stub: tests call the real Gemini API with keys from `.env`.

**Prompt strategy:** system/user split. System prompts live in `src/prompts/*.md` (`plan.md`, `generate_code.md`, `inspect.md`, `followups.md`). `generate_code` requests a **fenced pandas code block** assigning the answer to a `result` variable (and, P4, an optional `chart`/`table` spec); the executor extracts and runs it. `inspect`/`finalize` request structured JSON (decision/assumptions/answer/followups) validated with Pydantic; on parse failure the node retries once then degrades. **No raw rows ever appear in any prompt** — prompts interpolate only the question, the profile, and bounded result summaries.

---

## Tools & Tool Calling

The single "tool" is the **local sandboxed pandas executor** — the agent does not call external APIs.

| Tool name | Description | Inputs | Output | Side-effects |
|-----------|-------------|--------|--------|--------------|
| `execute_local` | Run an LLM-generated pandas snippet over the in-scope dataframe(s) in a restricted namespace. | code string, dataframe(s) for the dataset | bounded result summary (scalars / small table / shape) or a captured error string | none external; reads the local file once into a cached dataframe; no network, no fs writes |

**Tool selection strategy:** forced — every non-trivial question goes through `generate_code` → `execute_local`. There is no tool-choice branching; the "choice" is *what code to write*.

**Tool failure handling:** a code exception is captured (not raised) into `state["exec_error"]`. P1: a single capture → finalize honestly notes the failure / `handle_error`. P3: `inspect` routes back to `generate_code` with the error for self-correction, up to the step cap; on cap exhaustion, finalize degrades to a flagged best-guess or an honest "couldn't compute" with the attempts shown.

---

## Agent State

```python
class AgentState(TypedDict, total=False):
    # Identity
    run_id: str                     # set at initialisation (analysis_run.id)
    dataset_id: str                 # which dataset to analyse
    conversation_id: str | None     # P2: thread this run belongs to

    # Input
    question: str                   # the user's natural-language question
    profile: dict                   # schema/profile (cols, dtypes, ranges, row count, P3 quality flags)
    history: list                   # P2: prior-turn summaries [{question, result_summary}] — NEVER raw rows

    # Pipeline data (populated progressively by nodes)
    plan: str                       # plan node output
    code: str                       # generate_code output (pandas snippet)
    result_summary: dict            # execute_local output (bounded; NEVER raw rows in full)
    exec_error: str | None          # captured code-execution error, if any
    step: int                       # current loop step (0-based)
    max_steps: int                  # hard cap (default 4) — bounds the iterate loop
    attempts: list                  # P3: [{code, result_summary|error}] per step, for timeline + history

    # Output
    answer: str                     # finalize: prose answer
    assumptions: list               # P3: flagged assumptions / uncertainty
    followups: list                 # P3: 2-3 suggested follow-up questions
    viz: dict | None                # P4: chart/table spec
    tokens: dict                    # {prompt, completion, total} accumulated across calls
    cost_usd: float                 # accumulated estimated cost
    status: str                     # "completed" | "failed"

    # Control
    error: str | None               # fatal (non-code) error → routes to handle_error
```

---

## Nodes / Steps

### `plan`
- **Reads:** `question`, `profile`, `history`.
- **Writes:** `plan`, `tokens`, `cost_usd`.
- **LLM call:** yes — Gemini, system `plan.md`, returns a short ordered plan. P1: may be a one-line plan; P3: a real numbered plan. Input is question + profile + history only.
- **External calls:** Gemini (on failure: retry in provider; persistent → set `error`).
- **Behaviour:** Lays out how to compute the answer from the schema. Entry node.

### `generate_code`
- **Reads:** `question`, `profile`, `plan`, `exec_error` (P3 — prior error for self-correction), `attempts`.
- **Writes:** `code`, `tokens`, `cost_usd`.
- **LLM call:** yes — Gemini, system `generate_code.md`, returns a fenced pandas snippet assigning `result` (P4: optional `chart`/`table`). Input is question + profile + plan (+ prior code/error) — never rows.
- **Behaviour:** Produces the pandas to run. On a retry it is given the prior code + error to fix.

### `execute_local`  *(no LLM — privacy boundary)*
- **Reads:** `code`, `dataset_id` (to load the cached dataframe).
- **Writes:** `result_summary` or `exec_error`, `attempts` (append), `step` (+1).
- **LLM call:** **no.** This is the only node that touches raw rows; they never leave the process.
- **Behaviour:** Runs `code` in a restricted namespace (whitelisted imports: pandas/numpy; no `open`, no `__import__`, no network) with `df` (or `dfs`, P4) bound to the dataset's dataframe. Captures `result` into a **bounded** summary (truncate large frames to head + shape; scalars verbatim). Exceptions captured into `exec_error`, not raised.

### `inspect`  *(P3 — reflection; in P1 this is a pass-through that always routes to finalize)*
- **Reads:** `question`, `plan`, `code`, `result_summary`, `exec_error`, `step`, `max_steps`.
- **Writes:** decision (via edge), `assumptions`, `tokens`, `cost_usd`.
- **LLM call:** yes (P3) — Gemini, system `inspect.md`, returns JSON `{decision: "answer"|"retry", reason, assumptions?}`.
- **Behaviour:** Judges whether the result actually answers the question. Good → finalize. Code error or wrong/empty result and `step < max_steps` → back to `generate_code`. Cap reached → finalize with flagged uncertainty.

### `finalize`
- **Reads:** `question`, `result_summary`, `assumptions`, `attempts`, (P4) `viz`.
- **Writes:** `answer`, `followups` (P3), `viz` (P4), `status="completed"`, final `tokens`/`cost_usd`.
- **LLM call:** yes — Gemini, phrases prose answer from the result summary; P3 also emits 2–3 follow-ups and surfaces assumptions; honest caveat if uncertain.
- **Behaviour:** Terminal success node. Persists the full run (code, result, tokens, cost, steps, timestamps).

### `handle_error`
- **Reads:** `error`, `run_id`.
- **Writes:** `status="failed"`.
- **Behaviour:** Marks the run failed with the surfaced message; logs with `run_id`. Terminal.

---

## Graph / Flow Topology

```
START
  │
  ▼
plan ──(error)──────────────► handle_error ──► END
  │
  ▼
generate_code ──(error)─────► handle_error
  │
  ▼
execute_local ──(error)─────► handle_error          (error = fatal/non-code; exec_error is data, not fatal)
  │
  ▼
inspect ──(decision=retry AND step<max_steps)──► generate_code   ┐  bounded loop (P3)
  │                                                              │
  └──(decision=answer OR step>=max_steps)──► finalize ──► END    ┘
```

In **P1**, `inspect` is a pass-through that always routes to `finalize` (single pass); the conditional retry edge is wired but the cap forces ≤1 code execution. In **P3**, `inspect` becomes a real reflection node and the loop iterates up to `max_steps`.

**Conditional edges:**

| Source node | Condition | Target |
|-------------|-----------|--------|
| `plan` | `state["error"]` is not None | `handle_error` |
| `plan` | else | `generate_code` |
| `generate_code` | `state["error"]` is not None | `handle_error` |
| `generate_code` | else | `execute_local` |
| `execute_local` | `state["error"]` is not None (non-code fatal) | `handle_error` |
| `execute_local` | else | `inspect` |
| `inspect` | `decision == "retry"` AND `step < max_steps` | `generate_code` |
| `inspect` | `decision == "answer"` OR `step >= max_steps` | `finalize` |

---

## Memory & Context

| Scope | Mechanism | What is stored |
|-------|-----------|----------------|
| **Within a run** | LangGraph state | plan, code, result summary, attempts, tokens, cost |
| **Across runs** | SQLite (`analysis_runs`, `run_steps`) | every question, the code that ran, result summary, tokens, cost, timestamps |
| **Conversation** (P2) | `conversations` + `messages` tables → `history` in state | prior-turn `{question, result_summary}` pairs — **never raw rows** — threaded into `plan`/`generate_code` |

**Context window management:** profiles and result summaries are bounded by construction (column metadata, not rows; truncated frames). Conversation history threaded as compact prior-turn summaries; if a thread grows large, oldest turns are summarised/dropped (sliding window). Raw rows are never candidates for the context window.

---

## Human-in-the-Loop Checkpoints

None as blocking gates. The **uncertainty** behaviour (P3) is the closest analogue: when confidence is low the agent surfaces a clarifying question or a flagged best-guess in the answer, but execution does not pause server-side — the user simply asks again. (Not a LangGraph interrupt.)

---

## Error Handling & Recovery

**Node-level:** each node wraps its work in try/except. A non-code fatal error (e.g. Gemini persistently down, dataset file missing) sets `state["error"]` and routes to `handle_error`. A **code-execution** error is *not* fatal — it is captured into `exec_error` and (P3) drives a self-correction retry.

**Graph-level (`handle_error`):** reads `error`, `run_id`; updates the run row → status `failed`, `error_message`, `completed_at`; logs with `run_id`; terminates.

**Resume / retry strategy:** runs are short and idempotent at the question level; a failed run is simply re-asked. No mid-run checkpoint resume (not needed for sub-30s runs). Provider-level retry/backoff handles transient LLM failures.

**Partial failure:** if `execute_local` can't produce a clean result within `max_steps`, `finalize` degrades honestly — best-guess clearly flagged, or "couldn't compute this reliably" with the attempted code shown — rather than fabricating. Honest caveat over false confidence is the rule.

---

## Observability

| Signal | What | Where |
|--------|------|-------|
| **Trace** | One `analysis_run` per question; one `run_step` per loop step (P3) | SQLite + structlog |
| **LLM calls** | Prompt/completion/total tokens, model, estimated cost per call, accumulated per run | `src/analysis/cost.py` → run row + structlog |
| **Code execution** | The exact code string, success/error, result summary, latency | `run_steps` + structlog |
| **Run outcome** | Status, total duration, total tokens, cost | `analysis_runs` row |
| **Daily total** (P4) | Sum of cost across runs per day | `GET /usage/daily` |
| **Live** (P4) | Step events + answer tokens streamed | SSE `GET /conversations/{id}/ask/stream` |

---

## Concurrency Model

- **Run isolation:** single user; runs are processed one question at a time per conversation. The graph is invoked synchronously per request (P1–P3); P4 streams the same run over SSE. `run_id` scopes all writes.
- **Parallel nodes within a run:** none — the loop is inherently sequential (each step depends on the prior result).
- **Checkpointing:** none (no human-in-the-loop, sub-30s runs). The compiled graph is a module-level singleton; per-run state is passed in fresh.

---

## Graph Assembly (`src/graph/agent.py`)

```python
graph = StateGraph(AgentState)

graph.add_node("plan", plan)
graph.add_node("generate_code", generate_code)
graph.add_node("execute_local", execute_local)
graph.add_node("inspect", inspect)            # P1: pass-through → finalize; P3: real reflection
graph.add_node("finalize", finalize)
graph.add_node("handle_error", handle_error)

graph.set_entry_point("plan")

graph.add_conditional_edges(
    "plan",
    lambda s: "handle_error" if s.get("error") else "generate_code",
    {"handle_error": "handle_error", "generate_code": "generate_code"},
)
graph.add_conditional_edges(
    "generate_code",
    lambda s: "handle_error" if s.get("error") else "execute_local",
    {"handle_error": "handle_error", "execute_local": "execute_local"},
)
graph.add_conditional_edges(
    "execute_local",
    lambda s: "handle_error" if s.get("error") else "inspect",
    {"handle_error": "handle_error", "inspect": "inspect"},
)
graph.add_conditional_edges(
    "inspect",
    after_inspect,   # "generate_code" if retry and step < max_steps else "finalize"
    {"generate_code": "generate_code", "finalize": "finalize"},
)

graph.add_edge("finalize", END)
graph.add_edge("handle_error", END)

agentic_ai = graph.compile()
```
