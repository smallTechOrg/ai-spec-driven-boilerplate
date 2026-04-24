# Agent Graph

## State

```python
class AgentState(TypedDict):
    # Identity
    run_id: str                         # UUID of the SearchRun record
    criteria: SearchCriteria            # country, industry, size range

    # Pipeline data (populated progressively)
    raw_companies: list[dict]           # [{name, domain, website}, ...]
    leads: list[LeadCreate]             # enriched lead objects ready to save (contacts populated after contact_node)

    # Control
    error: str | None                   # set by any node on fatal failure
```

---

## Nodes

### `search_node`

**Reads from state:** `run_id`, `criteria`

**Writes to state:** `raw_companies`, `error`

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini API (Search Grounding) | `generate_content` with search-grounded prompt | Fatal — set `error`, transition to `handle_error` |

**Behaviour:** Builds a structured prompt asking Gemini (with Google Search Grounding enabled) to return a JSON array of EU SMBs matching the criteria. Parses the response into `raw_companies`. If parsing fails or the API errors, sets `error` and stops.

### `contact_node`

**Reads from state:** `run_id`, `leads`

**Writes to state:** `leads` (each LeadCreate gains a populated `contacts` list)

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini API | `generate_content` per lead (public contact extraction) | Partial — log and skip; continue with empty contacts |

**Behaviour:** For each lead in `leads`, calls Gemini with a `<node:contact>`-tagged prompt asking for up to 3 publicly-discoverable business contacts (decision-makers, data/tech leads). The prompt explicitly restricts results to public sources only (company website, LinkedIn public profiles, press releases). Returns each contact as `{name, title, email, phone, linkedin_url}` with nulls for unavailable fields. Emits a progress event per company. Partial failures are logged and skipped (empty contacts list for that lead).

### `enrich_node`

**Reads from state:** `run_id`, `raw_companies`

**Writes to state:** `leads`, `error`

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini API | `generate_content` per company (structured extraction) | Partial — log and skip that company; continue with others |

**Behaviour:** For each entry in `raw_companies`, calls Gemini with a structured extraction prompt (tagged `<node:enrich>`) asking for: industry, headcount band, and a 2-sentence "why fit" summary. Accumulates results into `leads`.

### `save_node`

**Reads from state:** `run_id`, `leads`

**Writes to state:** nothing (side-effectful)

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| PostgreSQL | `upsert` leads; update `SearchRun.status` | Fatal — set `error` |

**Behaviour:** Upserts each `Lead` (dedup on `domain`); updates the `SearchRun` record to `completed` with `lead_count` and `completed_at`. If a DB error occurs, marks run as `failed`.

### `handle_error`

**Reads from state:** `run_id`, `error`

**Writes to state:** nothing (side-effectful)

**Behaviour:** Updates the `SearchRun` record to `status = failed` and sets `error_message`. Always transitions to END.

---

## Edge Topology

```
START
  │
  ▼
search_node ──(error set)──► handle_error ──► END
  │
  ▼
enrich_node ──(error set)──► handle_error ──► END
  │
  ▼
contact_node ──(error set)──► handle_error ──► END
  │
  ▼
save_node ──(error set)──► handle_error ──► END
  │
  ▼
END
```

Routing rule: after each node, if `state["error"]` is not None, route to `handle_error`; otherwise continue to the next node.
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
