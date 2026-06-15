# Agent Graph

## State

```python
class AgentState(TypedDict, total=False):
    # Identity
    run_id: str
    query_record_id: str
    dataset_id: str

    # Pipeline data
    question: str
    csv_path: str
    column_names: list[str]
    row_count: int
    data_sample: str        # first 5 rows as CSV string, for context
    answer: str             # populated by analyze node

    # Control
    error: str | None
```

---

## Nodes

### `load_data`

**Reads from state:** `csv_path`, `dataset_id`

**Writes to state:** `column_names`, `row_count`, `data_sample`

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| Local filesystem | Read CSV with pandas | Fatal — set `error`, route to `handle_error` |

**Behaviour:** Reads the CSV file from disk using pandas. Extracts column names, row count, and the first 5 rows as a CSV string for LLM context. Writes these to state.

---

### `analyze`

**Reads from state:** `question`, `column_names`, `data_sample`, `run_id`

**Writes to state:** `answer`

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| Google Gemini (or stub) | Chat completion with schema + question | Fatal — set `error`, route to `handle_error` |

**Behaviour:** Constructs a prompt containing the column names, a sample of the data, and the user's question. Sends to Gemini (or stub). Writes the plain-text answer to state.

Stub tag injected into prompt: `<node:analyze>`

---

### `finalize`

**Reads from state:** `run_id`, `query_record_id`, `answer`

**Writes to state:** _(none — side-effects only)_

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | Update QueryRecord status=completed, write answer | Fatal — set `error` |
| SQLite | Update AgentRun status=completed | Fatal — set `error` |

**Behaviour:** Persists the answer to the QueryRecord. Updates AgentRun to `completed`.

---

### `handle_error`

**Reads from state:** `error`, `run_id`, `query_record_id`

**Writes to state:** _(none — side-effects only)_

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | Update QueryRecord status=failed, error_message | Best-effort |
| SQLite | Update AgentRun status=failed, error_message | Best-effort |

**Behaviour:** Persists failure state to the database. Logs error with run_id context. Terminates graph.

---

## Edge Topology

```
START
  │
  ▼
load_data ──(error)──► handle_error ──► END
  │
  ▼
analyze ──(error)──► handle_error
  │
  ▼
finalize ──(error)──► handle_error
  │
  ▼
END
```

---

## Graph Assembly

```python
graph = StateGraph(AgentState)

graph.add_node("load_data", load_data)
graph.add_node("analyze", analyze)
graph.add_node("finalize", finalize)
graph.add_node("handle_error", handle_error)

graph.set_entry_point("load_data")

graph.add_conditional_edges("load_data", after_load_data,
    {"analyze": "analyze", "handle_error": "handle_error"})
graph.add_conditional_edges("analyze", after_analyze,
    {"finalize": "finalize", "handle_error": "handle_error"})
graph.add_conditional_edges("finalize", after_finalize,
    {"end": END, "handle_error": "handle_error"})
graph.add_edge("handle_error", END)

compiled_graph = graph.compile()
```

---

## Concurrency Model

- One query runs at a time per user request (HTTP request per query, synchronous).
- No checkpointing in v0.1.
