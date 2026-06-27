# Agent Design

## Framework

LangGraph (StateGraph). Chosen because the analysis flow has a conditional error branch and needs checkpointable state to track run status in SQLite. The pattern is a lightweight **Tool Use + Exception Handling** graph (patterns #5 and #12 from the catalogue): one substantive node that calls Gemini and executes pandas code, with a conditional edge to either finalize or handle the error.

## LLM Provider and Model

| Agent / Node | Provider | Model ID | Rationale |
|-------------|----------|----------|-----------|
| analyze_data | Google Gemini | gemini-2.5-pro | High capability for code generation and structured JSON output; configurable via AGENT_LLM_MODEL env var |

**Fallback behaviour:** On Gemini API error (network timeout, rate limit, 5xx), the node sets `state["error"]` with the error message, the graph routes to `handle_error`, the Run record is marked "failed", and the API returns HTTP 500 with a clear message. No retry in Phase 1 (added in Phase 3).

**Prompt strategy:** Single system+user prompt. System sets the JSON output contract. User block contains: column schema as a table, the first 20 sample rows as CSV text, and the user's question. Gemini is instructed to return a single JSON object with exactly these keys: `pandas_code`, `chart_type`, `labels`, `values`, `summary`. No tool_use / function-calling — plain JSON mode via response instruction in the prompt.

## Agent State

```python
class AgentState(TypedDict):
    # Identity
    run_id: str                  # UUID string, set at graph invocation

    # Input (set before graph is invoked)
    dataset_id: str | None       # UUID of the dataset row in SQLite
    question: str | None         # The user's plain-English question

    # Pipeline data (set by analyze_data node)
    chart_type: str | None       # "bar" | "line" | "scatter"
    labels: list | None          # Real labels from pandas execution (not Gemini's illustrative values)
    values: list | None          # Real values from pandas execution (not Gemini's illustrative values)
    summary: str | None          # Written summary from Gemini

    # Control
    error: str | None            # Set by any node on failure; routes graph to handle_error
```

## Nodes

### `analyze_data(state: AgentState) -> AgentState`

**Reads from state:** `run_id`, `dataset_id`, `question`

**Writes to state:** `chart_type`, `labels`, `values`, `summary`, `error` (on failure)

**LLM call:** Yes — Gemini 2.5 Pro. Prompt contains: column schema (name + dtype per column) + first 20 sample rows as CSV text + user question. Expected output: JSON with `pandas_code`, `chart_type`, `labels`, `values`, `summary`.

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite (datasets table) | SELECT by dataset_id | Set state["error"]; route to handle_error |
| Local filesystem | pandas.read_csv / read_excel from file_path | Set state["error"]; route to handle_error |
| Gemini 2.5 Pro API | Generate pandas code + chart config + summary | Set state["error"]; route to handle_error |

**Behaviour:** Loads the Dataset record from SQLite using `dataset_id`. Reads the full DataFrame from `file_path` using pandas. Builds the Gemini prompt from `columns_json` (column schema) and `sample_rows_json` (up to 20 rows as CSV text) — the full DataFrame is NEVER included in the prompt. Calls Gemini and parses the JSON response. Executes `pandas_code` in a restricted namespace to get real labels and values. Returns state with `chart_type`, `labels`, `values`, `summary` set.

**Privacy rule (enforced in this node):** The Gemini prompt contains ONLY the column schema and up to 20 sample rows. The `file_path` DataFrame is loaded locally for pandas execution only — it is never serialized into the prompt.

**Safe pandas execution:**
```python
namespace = {"df": df, "pd": pd}
exec(pandas_code, namespace)
result = namespace.get("result")
# result must be: {"labels": [...], "values": [...]}
```
If `result` is missing, not a dict, or missing required keys, treat as execution error and set state["error"].

---

### `handle_error(state: AgentState) -> AgentState`

**Reads from state:** `run_id`, `error`

**Writes to state:** no new state fields (side effect only: updates Run record in DB)

**LLM call:** No

**Behaviour:** Updates the Run record in SQLite: sets status="failed", error_message=state["error"], completed_at=now(). Logs the error with run_id context.

---

### `finalize(state: AgentState) -> AgentState`

**Reads from state:** `run_id`, `chart_type`, `labels`, `values`, `summary`

**Writes to state:** no new state fields (side effect only: updates Run record in DB)

**LLM call:** No

**Behaviour:** Updates the Run record in SQLite: sets status="completed", completed_at=now(). Returns state unchanged.

## Graph Topology

```
START
  │
  ▼
analyze_data
  │
  ├── (error is set) ──► handle_error ──► END
  │
  └── (no error) ──────► finalize ──────► END
```

**Conditional edges:**

| Source node | Condition | Target |
|-------------|-----------|--------|
| analyze_data | `state.get("error") is not None` | handle_error |
| analyze_data | `state.get("error") is None` | finalize |
| handle_error | always | END |
| finalize | always | END |

## Graph Assembly (`src/graph/graph.py`)

```python
from langgraph.graph import StateGraph, END
from .nodes import analyze_data, handle_error, finalize
from .state import AgentState

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("analyze_data", analyze_data)
    graph.add_node("handle_error", handle_error)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("analyze_data")

    graph.add_conditional_edges(
        "analyze_data",
        lambda s: "handle_error" if s.get("error") else "finalize",
    )

    graph.add_edge("handle_error", END)
    graph.add_edge("finalize", END)

    return graph.compile()

compiled_graph = build_graph()
```

## Prompt (`src/prompts/analyze.md`)

Replaces `src/prompts/transform.md`. The prompt instructs Gemini to:
1. Analyze the provided column schema and sample data
2. Return ONLY a single JSON object (no markdown fences, no explanation text)
3. The JSON object must have exactly these keys:
   - `pandas_code` (string): executable Python code using `df` and `pd` that assigns `result = {"labels": [...], "values": [...]}` — labels are category/x-axis values, values are numeric y-axis values
   - `chart_type` (string): one of "bar", "line", "scatter" — chosen to best fit the question
   - `labels` (array): illustrative labels matching the code's intent (replaced by real execution)
   - `values` (array): illustrative values matching the code's intent (replaced by real execution)
   - `summary` (string): 2-3 sentence plain-English summary of key findings

The prompt template receives two variables: `{schema_text}` (column schema as a markdown table) and `{sample_csv}` (first 20 rows as CSV text) and `{question}` (the user's question).

## Memory and Context

| Scope | Mechanism | What is stored |
|-------|-----------|----------------|
| Within a run | LangGraph AgentState (in-memory) | All pipeline data for one analysis request |
| Across runs | SQLite Run table | Run status, error messages, timestamps |
| Dataset persistence | SQLite Dataset table + local filesystem | Uploaded file + schema + sample rows |
| Conversation | None in Phase 1 | Single-turn: one question → one chart+summary |

> **Assumed:** Conversation history (multi-turn chat memory linking prior questions and results) is deferred to Phase 3. Phase 1 is single-turn: each question is independent. This is appropriate because each analysis stands on its own chart and the user can scroll to see prior results.

**Context window management:** The prompt is bounded by schema size + 20 sample rows, which is small for any reasonable CSV. No truncation needed in Phase 1.

## Human-in-the-Loop Checkpoints

None in Phase 1. The analysis is fully automatic. Human testing gates exist between phases (see roadmap), not within the graph.

## Error Handling and Recovery

**Node-level:** Each node is wrapped in try/except. Any exception sets `state["error"]` to the exception message string and returns. The conditional edge routes to `handle_error`.

**Graph-level:** `handle_error` writes the failure to SQLite and terminates. The FastAPI route reads the final state; if `state["error"]` is set, it returns HTTP 500.

**Resume/retry:** No resume in Phase 1 — failed runs are terminal. Retries added in Phase 3.

**Partial failure:** There is one substantive node; failure is always fatal (routes to handle_error, returns 500).

## Observability

| Signal | What | Where |
|--------|------|-------|
| Run lifecycle | Status transitions (running → completed/failed) | SQLite runs table |
| Errors | Exception message + run_id | SQLite runs table + stderr log |
| LLM calls | Prompt size (tokens estimated), model name | stdout structured log |

Distributed tracing and LangSmith integration are deferred to Phase 3 (Agentic Stack Upgrade).

## Concurrency Model

- **Run isolation:** One analysis request per HTTP call; FastAPI handles concurrent requests via its async event loop, but each LangGraph invocation is synchronous and independent (scoped by run_id)
- **Parallel nodes within a run:** None — single linear path (analyze_data → finalize/handle_error)
- **Checkpointing:** None in Phase 1 (no human-in-the-loop, no long-running sessions); MemorySaver can be added in Phase 3 if needed
