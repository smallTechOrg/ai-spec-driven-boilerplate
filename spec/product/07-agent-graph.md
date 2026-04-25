# Agent Graph

## State

```python
class AgentState(TypedDict):
    # Identity
    run_id: str                         # UUID of the SourcingRun
    project_name: str

    # Pipeline input (set by intake_node)
    materials: list[dict]               # [{name, quantity, unit}, ...]

    # Pipeline data (populated progressively by nodes)
    supplier_candidates: dict[str, list[dict]]   # material_name → list of candidates
    recommendations: dict[str, list[dict]]       # material_name → ranked list
    report_summary: str                          # narrative summary from LLM

    # Control
    error: str | None                   # set by any node on fatal failure
```

---

## Nodes

### `intake_node`

**Reads from state:** `run_id`

**Writes to state:** `project_name`, `materials`

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| PostgreSQL | SELECT SourcingRun + MaterialLineItem rows | Fatal: set error, abort |
| PostgreSQL | UPDATE SourcingRun status → running | Fatal: set error, abort |

**Behaviour:** Loads the SourcingRun and its MaterialLineItem rows from PostgreSQL, sets status to "running", and populates `materials` in state.

---

### `research_node`

**Reads from state:** `run_id`, `materials`

**Writes to state:** `supplier_candidates`

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| Google Gemini (or stub) | For each material: prompt LLM to return ≥3 supplier candidates | Partial: log error, set empty list for that material; do not abort run |

**Behaviour:** Iterates over each material line item and calls the LLM provider to discover candidate suppliers. Assembles results into `supplier_candidates` keyed by material name. Stub returns 3 hardcoded candidates per material tagged `<node:research>`.

---

### `rank_node`

**Reads from state:** `run_id`, `materials`, `supplier_candidates`

**Writes to state:** `recommendations`

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| PostgreSQL | INSERT SupplierRecommendation rows | Fatal: set error, abort |

**Behaviour:** For each material, applies the weighted scoring formula (price 40%, lead_time 35%, certifications 25%) to rank candidates. Inserts ranked `SupplierRecommendation` rows into PostgreSQL. Weights are configurable via env vars.

---

### `report_node`

**Reads from state:** `run_id`, `recommendations`, `project_name`

**Writes to state:** `report_summary`

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| Google Gemini (or stub) | Generate narrative summary of top recommendations | Partial: log error, use auto-generated summary string |
| PostgreSQL | UPDATE SourcingRun status → completed, completed_at | Fatal: set error |

**Behaviour:** Calls the LLM to produce a plain-text narrative justifying the rank-1 selections. Updates the SourcingRun to status=completed. Stub produces a templated summary string.

---

### `handle_error_node`

**Reads from state:** `run_id`, `error`

**Writes to state:** _(none — terminal node)_

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| PostgreSQL | UPDATE SourcingRun status → failed, error_message, completed_at | Best-effort; log if DB also fails |

**Behaviour:** Sets the run to failed status, records the error message, and terminates the graph.

---

## Edge Topology

```
START
  │
  ▼
intake_node ──(error)──► handle_error_node ──► END
  │
  ▼
research_node ──(error)──► handle_error_node
  │
  ▼
rank_node ──(error)──► handle_error_node
  │
  ▼
report_node ──(error)──► handle_error_node
  │
  ▼
END
```

---

## Error Handler Node (`handle_error_node`)

- Reads: `state["error"]`, `state["run_id"]`
- Updates DB: SourcingRun status → "failed", error_message = state["error"], completed_at = now()
- Logs error with run_id context
- Terminates graph (routes to END)

---

## Finalize / Report Node (`report_node`)

- Reads: `state["run_id"]`, `state["recommendations"]`, `state["project_name"]`
- Updates DB: SourcingRun status → "completed", completed_at = now()
- Sets `state["report_summary"]` for display in UI
- Logs run summary with material count and recommendation count

---

## Graph Assembly (`src/lead_gen_agent/graph/graph.py`)

```python
from langgraph.graph import StateGraph, END
from .nodes import intake_node, research_node, rank_node, report_node, handle_error_node
from .state import AgentState

def _route(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "__next__"

graph = StateGraph(AgentState)

graph.add_node("intake", intake_node)
graph.add_node("research", research_node)
graph.add_node("rank", rank_node)
graph.add_node("report", report_node)
graph.add_node("handle_error", handle_error_node)

graph.set_entry_point("intake")

graph.add_conditional_edges("intake",   lambda s: "handle_error" if s.get("error") else "research")
graph.add_conditional_edges("research", lambda s: "handle_error" if s.get("error") else "rank")
graph.add_conditional_edges("rank",     lambda s: "handle_error" if s.get("error") else "report")
graph.add_conditional_edges("report",   lambda s: "handle_error" if s.get("error") else END)
graph.add_edge("handle_error", END)

compiled_graph = graph.compile()
```

---

## Concurrency Model

- **Multiple concurrent runs supported** — each run is independent (separate run_id, separate DB rows)
- Runs are executed as background asyncio tasks spawned by the FastAPI POST /api/runs endpoint
- **No checkpointing in v0.1** — if the process restarts mid-run, the run remains in "running" status; a startup cleanup job (future) will mark orphaned runs as failed
- LangGraph's in-memory runner is used; no SqliteSaver/PostgresSaver needed for v0.1
