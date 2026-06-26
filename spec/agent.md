# Agent

## Agent Architecture Pattern

**Chosen:** Graph (LangGraph) — Prompt Chaining + Tool Use + Exception Handling + Recovery (§1, §5, §12 from `harness/patterns/agentic-ai.md`)

The pipeline has a fixed, ordered sequence of steps with no user-driven branching: `parse_csv` feeds `answer_question` (Phase 1); Phase 2 inserts `generate_code` and `execute_code` between `parse_csv` and `answer_question`. LangGraph's `StateGraph` models this as a directed acyclic graph with a single conditional error branch at every node. The Tool Use pattern applies because the LLM call is a real external call (Gemini API). The Prompt Chaining pattern applies because `parse_csv` output (schema + sample rows) feeds the `answer_question` prompt. Exception Handling applies at every node.

---

## LLM Provider & Model

| Node | Provider | Model ID | Rationale |
|------|----------|----------|-----------|
| `answer_question` | Google Gemini via `google-genai` SDK | `gemini-2.0-flash` (configurable via `AGENT_LLM_MODEL`) | Fast, low-latency text answer generation |
| `generate_code` (Phase 2) | Google Gemini via `google-genai` SDK | `gemini-2.0-flash` (configurable via `AGENT_LLM_MODEL`) | Code generation; same model keeps env config simple |

**No LangChain.** All Gemini calls use the `google-genai` Python SDK directly via the existing `src/llm/client.py` (`LLMClient` / `GeminiProvider`). There is no LangSmith tracing.

**Fallback behaviour:** On a Gemini API error (4xx/5xx/timeout), the node catches the exception, sets `state["error"]` with a human-readable message, and the conditional edge routes to `handle_error`. No silent retry in Phase 1.

**Prompt strategy:** Each LLM call uses a system prompt loaded from the relevant Markdown file under `src/prompts/`. The `answer_question` node uses `src/prompts/answer_question.md`. The `generate_code` node (Phase 2) uses `src/prompts/generate_code.md`. Both call `LLMClient.complete()` with the system prompt and a user message assembled from the state.

---

## Agent State

```python
from typing import TypedDict, Any


class AgentState(TypedDict, total=False):
    # --- Identity (set at initialisation by runner.py) ---
    run_id: str          # UUID of the ConversationRun DB record
    session_id: str      # UUID of the Session
    question: str        # Natural-language question from the user

    # --- CSV context (populated by parse_csv) ---
    column_schema: list[dict]   # [{"name": "col", "dtype": "float64"}, ...]
    sample_rows: list[dict]     # First 10 rows of the DataFrame as list of dicts

    # --- Pipeline data (populated progressively by nodes) ---
    answer: str                  # Plain-English answer from answer_question
    generated_code: str | None   # Python code string from generate_code (Phase 2)
    executed_code: str | None    # Code that was actually executed (Phase 2)
    chart_base64: str | None     # Base64-encoded PNG from execute_code (Phase 2)
    chart_type: str | None       # "bar" | "line" | "scatter" | None (Phase 2)
    node_trace: list[str]        # Names of nodes that ran, in order

    # --- Control ---
    error: str | None    # Set by any node on fatal failure; routes to handle_error
    status: str          # "pending" | "completed" | "failed"
```

All fields are `total=False` (optional) because LangGraph merges partial dicts returned from each node into the running state — a node only needs to return the fields it writes.

---

## Nodes / Steps

### `parse_csv` (Phase 1)

**Reads from state:** `session_id`

**Writes to state:** `column_schema`, `sample_rows`, `node_trace` (appends `"parse_csv"`), or `error`

**LLM call:** No

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| In-memory session store | `SESSION_STORE[session_id]` lookup | Fatal — sets `state["error"]`, routes to `handle_error` |

**Behaviour:** Looks up the pandas DataFrame from `SESSION_STORE` using `state["session_id"]`. Extracts column names and dtypes as `column_schema` (list of `{"name": col, "dtype": str(dtype)}`). Serialises the first 10 rows as `sample_rows` (list of dicts, NaN values replaced with `None`). Emits a structured log line with `session_id`, column count, and row count. If the session is not found in the store, sets `state["error"]` and returns immediately.

---

### `answer_question` (Phase 1)

**Reads from state:** `column_schema`, `sample_rows`, `question`

**Writes to state:** `answer`, `node_trace` (appends `"answer_question"`), or `error`

**LLM call:** Yes — `LLMClient.complete()` using `GeminiProvider` with model `gemini-2.0-flash`, system prompt from `src/prompts/answer_question.md`.

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini API | `LLMClient.complete(system_prompt, user_message)` | Fatal — sets `state["error"]`, routes to `handle_error` |

**Behaviour:** Constructs a user message containing the column schema (formatted as a Markdown table), the first 10 sample rows (formatted as a Markdown table), and the user's question. Calls Gemini with the system prompt and user message. Stores the response text as `state["answer"]`. Emits a structured log line with `question` (truncated to 100 chars) and answer character count. On any exception, sets `state["error"]`.

---

### `generate_code` (Phase 2)

**Reads from state:** `column_schema`, `sample_rows`, `question`

**Writes to state:** `generated_code`, `node_trace` (appends `"generate_code"`), or `error`

**LLM call:** Yes — `LLMClient.complete()` using `GeminiProvider` with model `gemini-2.0-flash`, system prompt from `src/prompts/generate_code.md`.

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini API | `LLMClient.complete(system_prompt, user_message)` | Fatal — sets `state["error"]`, routes to `handle_error` |

**Behaviour:** Constructs a user message with the column schema, sample rows, and question — instructing Gemini to produce a self-contained Python code block that:
1. Receives a variable `df` (the pandas DataFrame).
2. Answers the question and prints the result.
3. Generates a matplotlib chart and saves it to a variable `fig` (a `matplotlib.figure.Figure`).

Stores the code string (extracted from the fenced code block in the response) as `state["generated_code"]`. If no fenced code block is found, sets `state["error"]`.

---

### `execute_code` (Phase 2)

**Reads from state:** `session_id`, `generated_code`

**Writes to state:** `executed_code`, `chart_base64`, `chart_type`, `node_trace` (appends `"execute_code"`), or `error`

**LLM call:** No

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| In-memory session store | `SESSION_STORE[session_id]` lookup | Fatal — sets `state["error"]` |
| Python `exec()` sandbox | Execute generated code | Fatal — sets `state["error"]` with the exception message |

**Behaviour:** Retrieves the DataFrame from `SESSION_STORE`. Executes `state["generated_code"]` in a restricted `exec()` environment with only `{"df": dataframe, "pd": pandas, "plt": matplotlib.pyplot, "io": io}` in scope. After execution, checks the local namespace for a `fig` variable (`matplotlib.figure.Figure`). If found, saves it to a `BytesIO` buffer as PNG and encodes it as base64 — stored as `state["chart_base64"]`. Determines `chart_type` from the figure's axes (first axes subplot type: "bar", "line", or "scatter"; defaults to "bar" if undetermined). Sets `state["executed_code"]` to the code that was executed. Emits a structured log line with execution duration and whether a chart was produced. On any exception during `exec()`, sets `state["error"]` with the traceback message.

**Sandbox constraints:** The exec namespace contains only `df`, `pd` (pandas), `plt` (matplotlib.pyplot), and `io`. No `os`, `sys`, `subprocess`, `open`, `__import__`, or builtins that touch the filesystem or network. The sandbox is enforced by passing an explicit restricted globals dict to `exec()`.

---

### `handle_error` (Phase 1+)

**Reads from state:** `error`, `run_id`

**Writes to state:** `status = "failed"`, `node_trace` (appends `"handle_error"`)

**LLM call:** No

**Behaviour:** Logs the error with `run_id` and `error` fields via structlog. Returns `{"status": "failed"}`. The runner reads `state["error"]` and `state["status"]` after the graph returns to write the `ConversationRun` record with `status="failed"`.

---

### `finalize` (Phase 1+)

**Reads from state:** `answer`, `chart_base64` (optional), `executed_code` (optional), `node_trace`

**Writes to state:** `status = "completed"`

**LLM call:** No

**Behaviour:** Sets `state["status"] = "completed"`. Emits a structured log line with `run_id` and `"completed"`. The runner reads the final state to write the `ConversationRun` record.

---

## Graph / Flow Topology

### Phase 1

```
START
  │
  ▼
parse_csv ──(error)──► handle_error ──► END
  │
  ▼
answer_question ──(error)──► handle_error ──► END
  │
  ▼
finalize ──► END
```

### Phase 2

```
START
  │
  ▼
parse_csv ──(error)──► handle_error ──► END
  │
  ▼
generate_code ──(error)──► handle_error ──► END
  │
  ▼
execute_code ──(error)──► handle_error ──► END
  │
  ▼
answer_question ──(error)──► handle_error ──► END
  │
  ▼
finalize ──► END
```

**Conditional edges:**

| Source node | Condition | Target |
|-------------|-----------|--------|
| `parse_csv` | `state.get("error")` is truthy | `handle_error` |
| `parse_csv` | no error | next node |
| `generate_code` | `state.get("error")` is truthy | `handle_error` |
| `generate_code` | no error | `execute_code` |
| `execute_code` | `state.get("error")` is truthy | `handle_error` |
| `execute_code` | no error | `answer_question` |
| `answer_question` | `state.get("error")` is truthy | `handle_error` |
| `answer_question` | no error | `finalize` |

---

## Memory & Context

| Scope | Mechanism | What is stored |
|-------|-----------|----------------|
| Within a run | LangGraph `AgentState` | All pipeline data — schema, sample rows, answer, code, chart |
| Across runs (session) | In-memory `SESSION_STORE` dict | The pandas DataFrame for the session (process lifetime only) |
| Persistent metadata | SQLite `sessions` + `conversation_runs` | Session metadata, question/answer text, status |
| Conversation context | None in Phase 1 | Each question is stateless; prior answers are not passed as context |

**Context window management:** The sample rows passed to `answer_question` and `generate_code` are capped at 10 rows. The column schema is always complete. For wide DataFrames (>50 columns) the schema is summarised as column names + dtypes only, without sample values, to stay within the context limit.

---

## Human-in-the-Loop Checkpoints

None. The pipeline runs fully autonomously from upload to answer. No human approval gates are inserted in the graph.

---

## Error Handling & Recovery

**Node-level:** Every node wraps its logic in `try / except Exception as exc`. On any exception, the node returns `{**state, "error": str(exc)}`. The subsequent conditional edge routes to `handle_error`.

**Graph-level (`handle_error` node):**
- Logs the error via structlog with `run_id` and `error` fields
- Returns `{"status": "failed"}`
- After the graph returns, `runner.py` writes `ConversationRun.status = "failed"` and `ConversationRun.error = state["error"]`
- The API returns HTTP 200 with `{"status": "failed", "error": "<message>"}` — not a 500

**Session not found:** Treated as a node-level error in `parse_csv`. The user sees: "Session not found. Please re-upload your CSV."

**Code execution error (Phase 2):** Treated as a node-level error in `execute_code`. The user sees the exception message. The text answer is not affected — `answer_question` still runs if the pipeline proceeds without `execute_code` errors. If `execute_code` fails, the graph routes to `handle_error` before `answer_question`.

**Resume / retry strategy:** No resume from checkpoint. A failed run requires a new `POST /sessions/{session_id}/questions` call.

---

## Observability

| Signal | What | Where |
|--------|------|-------|
| Structured log — node entry | `node_name`, `run_id`, `session_id` | structlog → stdout JSON |
| Structured log — node exit | `node_name`, `run_id`, `duration_ms` | structlog → stdout JSON |
| Structured log — Gemini call | `model`, `prompt_length`, `response_length`, `duration_ms` | structlog → stdout JSON |
| Structured log — CSV parse | `session_id`, `col_count`, `row_count` | structlog → stdout JSON |
| Structured log — code execution | `duration_ms`, `chart_produced: bool` | structlog → stdout JSON |
| Run outcome | `run_id`, `status`, `error` | SQLite `conversation_runs` + structlog |

No LangSmith or external tracing service. All observability is structlog to stdout.

---

## Concurrency Model

- **Run isolation:** Each `POST /sessions/{session_id}/questions` call is synchronous and fully isolated by `run_id`. Multiple concurrent requests are handled by Uvicorn worker threads.
- **Session store thread safety:** `SESSION_STORE` is a plain Python dict. For Phase 1 with a single Uvicorn worker this is safe. For multi-worker deployments, a thread-safe dict or shared memory layer would be needed (out of scope).
- **Parallel nodes within a run:** None. The pipeline is strictly sequential.
- **Checkpointing:** None. The graph runs to completion or error without mid-run persistence.

---

## Graph Assembly (`src/graph/agent.py`)

### Phase 1

```python
from langgraph.graph import StateGraph, END
from src.graph.state import AgentState
from src.graph.nodes import parse_csv, answer_question, handle_error, finalize
from src.graph.edges import route_or_error


def _build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("parse_csv", parse_csv)
    g.add_node("answer_question", answer_question)
    g.add_node("handle_error", handle_error)
    g.add_node("finalize", finalize)

    g.set_entry_point("parse_csv")

    g.add_conditional_edges(
        "parse_csv",
        lambda s: route_or_error(s, "answer_question"),
    )
    g.add_conditional_edges(
        "answer_question",
        lambda s: route_or_error(s, "finalize"),
    )

    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)

    return g.compile()


# Module-level singleton
agentic_ai = _build_graph()
```

### Phase 2 additions

```python
# Additional nodes registered in _build_graph():
g.add_node("generate_code", generate_code)
g.add_node("execute_code", execute_code)

# Entry point unchanged; after parse_csv:
g.add_conditional_edges(
    "parse_csv",
    lambda s: route_or_error(s, "generate_code"),
)
g.add_conditional_edges(
    "generate_code",
    lambda s: route_or_error(s, "execute_code"),
)
g.add_conditional_edges(
    "execute_code",
    lambda s: route_or_error(s, "answer_question"),
)
# answer_question and finalize edges unchanged
```

`route_or_error` in `src/graph/edges.py`:

```python
def route_or_error(state: AgentState, next_node: str) -> str:
    if state.get("error"):
        return "handle_error"
    return next_node
```
