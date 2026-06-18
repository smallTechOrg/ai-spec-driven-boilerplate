# Agent Graph

> **Boilerplate status:** Required when the project uses an agent framework (LangGraph, CrewAI, AutoGen, etc.). Filled in by the tech-designer as part of the tech design stage. Delete this file if there's no agent framework (a simple script or API). The spec-reviewer treats it as a **CRITICAL BLOCKER** — the tech design is not approved if it's absent or incomplete when a framework is in use.
>
> **If the agent acts on the outside world** (tools, data, search), it must use a **ReAct loop**. Fill this file in per [`../engineering/patterns/react-agent.md`](../engineering/patterns/react-agent.md) — answer its eight pre-coding questions, carry the loop-control + usage fields in State, route iteration exhaustion to `force_finalize` (not a one-shot pipeline), and surface `action_history` to the user live. The Force-Finalize node section below applies only to ReAct loops.
>
> **This graph wires the stack layers** declared in `02-architecture.md` § Agentic stack layers used: a context-assembly step pulls memory + retrieval ([`memory-and-context.md`](../engineering/patterns/memory-and-context.md), [`retrieval.md`](../engineering/patterns/retrieval.md)); `act` calls tools/MCP behind the action-safety boundary ([`tools-and-mcp.md`](../engineering/patterns/tools-and-mcp.md)); high-stakes actions route through guardrails/HITL ([`guardrails-and-hitl.md`](../engineering/patterns/guardrails-and-hitl.md)). For multi-agent, each sub-agent is its own subgraph ([`multi-agent.md`](../engineering/patterns/multi-agent.md)); for resumable runs, compile with a checkpointer ([`durability.md`](../engineering/patterns/durability.md)).

---

## State

<!-- FILL IN: Define the agent's state type. Every field must be named and typed. -->

```python
class AgentState(TypedDict):
    # Identity
    run_id: int
    # ... add all fields

    # Pipeline data (populated progressively by nodes)
    # ...

    # Control
    error: str | None   # set by any node on fatal failure

    # ReAct loop only (omit for one-shot pipelines)
    action_history: list[dict]  # [{"action": str, "result": str, "is_error": bool}]
    iteration_count: int        # guarded against max_iterations → force_finalize
    llm_response: str           # raw last LLM output — router checks it for FINAL ANSWER

    # Usage accounting (persist on the run record — see patterns/react-agent.md § State)
    tokens_input: int
    tokens_output: int
    estimated_cost_usd: float | None
```

---

## Nodes

<!-- FILL IN: One section per node. -->

### `node_[name]`

**Reads from state:** <!-- field names -->

**Writes to state:** <!-- field names -->

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| <!-- system --> | <!-- what it calls --> | <!-- fatal (set error) or partial (log and continue) --> |

**Behaviour:** <!-- one paragraph describing what this node does -->

---

## Edge Topology

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

## Force-Finalize Node (`node_force_finalize`) — ReAct loops only

<!-- FILL IN (ReAct agents only): best-effort close-out when iterations run out. Delete for one-shot pipelines. -->

- Reached when `iteration_count` hits `max_agent_iterations` or the last N actions all errored (see `../engineering/patterns/react-agent.md`) — **not** a fatal error.
- Asks the LLM to synthesise the best answer it can from `action_history`, noting what is missing; never emits a bare "I couldn't answer."
- Updates DB: run status → "completed" (records the early-exit reason); persists `action_history` + usage fields.
- Releases the run's module-level resources (same cleanup as `finalize`).

---

## Graph Assembly (`graph/agent.py`)

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
