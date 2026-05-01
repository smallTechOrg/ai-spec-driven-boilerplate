# Agent Graph

> **Note:** Food Tracker uses a simple linear pipeline, not a framework like LangGraph or CrewAI. There is no `StateGraph`. This file documents the pipeline state and node sequence in the same format for reference.

## State

```python
class FoodState(TypedDict):
    # Identity
    run_id: int                   # FoodLog.id assigned after DB insert

    # Input
    image_bytes: bytes            # Raw bytes of the uploaded photo
    image_filename: str           # Original filename (for logging)

    # Analysis output (populated by node_analyse_food)
    food_name: str | None
    calories_kcal: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    provider: str                 # "gemini" or "stub"

    # Control
    error: str | None             # Set by any node on fatal failure
```

## Nodes

### `node_analyse_food`

**Reads from state:** `image_bytes`, `image_filename`

**Writes to state:** `food_name`, `calories_kcal`, `protein_g`, `carbs_g`, `fat_g`, `provider`

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| LLMClient (Gemini or Stub) | Upload image bytes + prompt, parse JSON response | Set `error`, abort pipeline |

**Behaviour:** Sends the image bytes and a structured prompt to the LLM provider. Parses the returned JSON into the four nutrition fields. If parsing fails, sets `error` and stops.

---

### `node_save_log`

**Reads from state:** `food_name`, `calories_kcal`, `protein_g`, `carbs_g`, `fat_g`, `provider`, `image_filename`

**Writes to state:** `run_id`

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| PostgreSQL | INSERT INTO food_logs | Set `error`, return HTTP 500 |

**Behaviour:** Writes one `FoodLog` row to PostgreSQL. Sets `run_id` to the new row's PK.

## Pipeline Topology

```
START
  |
  v
node_analyse_food --(error)--> END (error state)
  |
  v
node_save_log ------(error)--> END (error state)
  |
  v
 END (success)
```

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
