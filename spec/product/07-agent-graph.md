# Agent Graph

## Not Applicable

This project does not use an agent framework (no LangGraph, CrewAI, AutoGen, or equivalent). The agent is a single stateless LLM call:

```
city (str)  →  build_prompt()  →  LLMProvider.call()  →  parse_response()  →  ItineraryResponse
```

No state machine, no graph, no multi-step pipeline. If scope expands (e.g., multi-step planning, tool use), this file will be updated and an agent framework will be introduced.

<!-- FILL IN: ASCII diagram of node flow. Show conditional edges explicitly. -->

```
START
  │
  ▼
node_a ──(error)──► node_handle_error ──► END
  │
  ▼
node_b
  │
  ▼
node_finalize
  │
  ▼
END
```

---

## Error Handler Node (`node_handle_error`)

<!-- FILL IN: What happens when a fatal error occurs. -->

- Reads: `state.error`, `state.run_id`
- Updates DB: run status → "failed", error_message, completed_at
- Logs error with run_id context
- Terminates graph

---

## Finalize Node (`node_finalize`)

<!-- FILL IN: How a successful run is closed out. -->

- Reads: `state.run_id`, `state.completed_*`, `state.failed_*`
- Updates DB: run status → "completed", posts_completed count, completed_at
- Logs run summary

---

## Graph Assembly (`agent/graph.py`)

<!-- FILL IN: Pseudocode showing how nodes and edges are wired. Must be ≤ 60 lines in the real file. -->

```python
graph = StateGraph(AgentState)

graph.add_node("node_a", node_a)
graph.add_node("node_b", node_b)
graph.add_node("finalize", node_finalize)
graph.add_node("handle_error", node_handle_error)

graph.set_entry_point("node_a")

# Conditional edges after nodes that can produce fatal errors
graph.add_conditional_edges(
    "node_a",
    lambda s: "handle_error" if s.get("error") else "node_b",
)

# Unconditional edges
graph.add_edge("node_b", "finalize")
graph.add_edge("finalize", END)
graph.add_edge("handle_error", END)

compiled_graph = graph.compile()
```

---

## Concurrency Model

<!-- FILL IN: How concurrent runs are handled. -->

- **One run at a time** (enforced at API layer — returns 409 if a run is already active)
- OR: **Parallel nodes** within a single run (describe which nodes run in parallel and why)
- **Checkpointing:** <!-- none / SqliteSaver / PostgresSaver — and when it's needed -->
