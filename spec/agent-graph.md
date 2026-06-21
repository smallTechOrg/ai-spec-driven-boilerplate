# Agent Graph

> **Placeholder.** The researcher fills every section thoroughly at intake — highly technical and exact, no vague prose.

<!--
SCOPE OF THIS FILE — read before filling.
This is the EXACT agent topology contract for any LLM/agent surface in the product:
the typed state object, every node (its state reads/writes + per-external-call failure policy),
the full edge topology including every conditional route, the error/finalize terminal nodes,
the compiled graph assembly, and the concurrency/checkpointing model.

OPTIONAL DOCUMENT: this file is REQUIRED whenever an agent framework or LLM call-graph is in
use (LangGraph, CrewAI, a hand-rolled node loop, even a single-node stub agent). The reviewer
treats a missing/empty agent-graph.md as a CRITICAL BLOCKER while an agent loop exists. DELETE
THIS FILE ENTIRELY only if the product has no agent loop and no LLM call-graph at all. A
single-node stub agent in Phase 1 is still an agent loop — keep and fill this file.

This is a WHAT-the-contract-is doc, not a HOW doc. State the typed contract, the node I/O
surface, the routing predicates, and the assembly shape. Line-by-line node bodies live in src/.

CROSS-REFERENCES (one fact, one place — link, never duplicate). Every link below MUST resolve
to a real, non-placeholder anchor; the reviewer rejects a dangling cross-reference:
  - State field meanings that mirror API payloads        → spec/api.md
  - audit_log columns (run_id, action, payload, duration_ms, …) → spec/data-model.md  (THE home)
  - stub_mode flag / offline-no-key behaviour            → spec/api.md (/health) + spec/architecture.md
  - LLM provider, model id, agent-framework version pin   → spec/architecture.md (Stack table)
  - Per-phase acceptance criteria PN-ACn                  → spec/delivery-plan.md
  - Product Success Criteria SC-N                         → spec/vision.md
  - Framework API gotchas (reducer trap, async savers)    → harness/patterns/langgraph.md  (CANONICAL — keep this path; it is a harness method-asset, NOT a spec/ doc)

The full product-spec set is exactly: spec/{vision,architecture,data-model,api,ui,agent-graph,delivery-plan}.md.
There is NO spec/features/, NO FR/CR file, NO spec/ROADMAP.md — deferred scope lives as LATER PHASES
in spec/delivery-plan.md. Do not cite any of those removed paths.

GAP MARKERS: use [NEEDS CLARIFICATION: q] ONLY for genuinely topology-changing unknowns
(e.g. "is there a human-in-the-loop interrupt?"). Use [ASSUMPTION: value] for everything
defaulted. NEVER leave a blank cell, a silent default, or a "TBD".
-->

---

## Open topology questions

<!--
FILL IN (MANDATORY — a blank is rejected): list every topology-changing unknown as a
[NEEDS CLARIFICATION: q] row below — e.g. "is there a human-in-the-loop interrupt?",
"does the planner loop until a budget, or run once?", "does any node fan out N parallel sub-calls?".
These are the questions whose answers would CHANGE the diagram or the node set.
If there are none, you MUST affirmatively write the single line: `No open topology questions.`
An empty section (neither a marker nor that exact line) is REJECTED at the pre-code gate.
-->

<!-- e.g. [NEEDS CLARIFICATION: does node_plan retry on empty result, or fall through to finalize?] -->
<!-- or the literal line: No open topology questions. -->

---

## State

<!--
FILL IN: the COMPLETE typed state object as a real TypedDict (or the chosen framework's state
class), grouped into four commented sections IN THIS ORDER:
  # Identity  — run/session/correlation ids, immutable for the run
  # Input     — what the caller supplied; matches the request body in spec/api.md
  # Pipeline  — fields populated PROGRESSIVELY by nodes; each starts None, a node fills it
  # Control   — error (MANDATORY) + any routing/iteration counters

HARD BAR:
  - Every field annotated `name: concrete-type` using REAL Python types: str, int, float, bool,
    list[Row], dict[str, X]. Optional is written `X | None`. A field that is empty until a node
    fills it MUST be `T | None` (not bare T).
  - `error: str | None` is MANDATORY and lives in # Control. Any node sets it on fatal failure.
  - NO field typed bare `Any`. If a field is genuinely dynamic, type it `dict[str, Any]` AND add a
    one-line `# why Any:` justification on that line. A field with no justification is rejected.
  - Each Pipeline field MUST be referenced by some node's Reads/Writes below. An orphan field
    (declared here, used by no node) is rejected. Conversely, no node may read/write a field that
    is not declared here.
  - If using LangGraph, DO NOT annotate a messages list with `Annotated[list, add_messages]` —
    see harness/patterns/langgraph.md (double-append trap). Type it `list[BaseMessage]` plain.

WEAK vs STRONG:
  weak  : `data: Any` / `result: dict` / `messages: list`   (no element type, no justification)
  strong: `rows: list[dict[str, str | int | float | None]] | None  # query result, None until executed`
-->

```python
from typing import TypedDict, Any   # Any only if a field is justified-dynamic below
# from langchain_core.messages import BaseMessage   # if a message transcript is carried

class AgentState(TypedDict):
    # Identity
    run_id: str               # <!-- UUIDv4, correlation id; mirrors audit_log.run_id (data-model.md) -->
    session_id: str           # <!-- caller session; one run per session at a time (see Concurrency) -->
    # <!-- add identity fields; all immutable for the run -->

    # Input
    # <!-- field: concrete-type — meaning; MUST match request body in spec/api.md -->

    # Pipeline (populated progressively; each None until its producing node writes it)
    # <!-- field: concrete-type | None — meaning; referenced by a node Writes below -->

    # Control
    error: str | None         # set by ANY node on fatal failure; routes to handle_error
    # <!-- iteration: int — loop counter, if a multi-step loop exists -->
    # <!-- next: str | None — routing hint, if a router node sets the next node name -->
```

<!-- FILL IN: one-row-per-field table mirroring the code above, so the contract is enumerable. -->

| Field | Group | Type | None until | Set by node | Read by node(s) |
|-------|-------|------|-----------|-------------|-----------------|
| `run_id` | Identity | `str` | n/a (set at init) | (entry init) | all |
| `error` | Control | `str \| None` | n/a (init `None`) | any node on fatal | `node_handle_error` |
| `<!-- field -->` | <!-- Input/Pipeline --> | `<!-- type -->` | <!-- node / n/a --> | `<!-- node -->` | `<!-- node(s) -->` |

---

## Nodes

<!--
FILL IN: ONE `###` subsection per node, in execution order. Node names are `node_<verb_noun>`
(snake_case). Every field a node names in Reads/Writes MUST exist in the State table above.

PER NODE, EXACTLY:
  - Reads:  comma-separated State field names this node reads.
  - Writes: comma-separated State field names this node writes (include `error` for any node
            that can fail fatally).
  - Serves: cite the SC-N (vision.md) AND the PN-ACn (delivery-plan.md) this node advances.
    "internal" is NOT a free pass: a node with no user-visible output MUST instead state
    `internal: serves <named downstream node> by producing <state field>` — naming the consumer
    and the field. A bare "internal" with no consumer+field is REJECTED.
  - I/O & Guard table (REQUIRED — replaces free-prose behaviour; the most load-bearing cell, so
    it is structured, not narrative). EXACTLY these four rows:
      | Prompt / data inputs | the State fields fed in (for an LLM node: which fields enter the
                               prompt; for a tool/DB node: which fields parameterise the call) |
      | Output field written | the SINGLE State field this node populates on success (must appear
                               in Writes and in the State table) |
      | Guard (predicate)    | a CHECKABLE boolean expression over state/output that MUST hold
                               for the write to be accepted — e.g. `sql.strip().upper().startswith("SELECT")`
                               or `len(rows) >= 0 and all(isinstance(r, dict) for r in rows)`.
                               PROSE IS REJECTED: the cell must read as a Python boolean expression
                               (mirror the State section's "no bare Any" rigor). |
      | On guard fail        | EXACTLY ONE of: `fatal: set state.error` / `partial: write <named
                               fallback value>` — naming the concrete fallback, not "continue". |
  - External-calls table (REQUIRED for any node that calls an LLM, DB, HTTP API, or tool):
      | System | Operation | Timeout | Retries (count, base_ms, cap_ms, jitter) | Idempotent? | Stub fallback | On failure |
    Column rules:
      - Operation: form `<verb> <object> (<model id / table / endpoint>)`, e.g.
        `NL→SQL completion (gemini-2.x, see architecture.md Stack)`. A bare "API call" / "LLM call"
        is REJECTED — name the verb, the object, AND the concrete model/table/endpoint.
      - Timeout: a concrete number with units (e.g. `30s`) or `[ASSUMPTION: 30s]`. Never blank.
      - Retries: `(count, base_ms, cap_ms, jitter y/n)` or the literal `no retry`. Never "TBD".
      - Idempotent?: `yes` / `no` (drives whether a retry is even safe).
      - Stub fallback: the EXACT deterministic value this node writes WHILE stub_mode is true /
        no key is set (e.g. `sql="SELECT 1 AS stub"`, `rows=[{"stub": true}]`). This is what
        AG-AC3 asserts. `none` is only valid for a node that makes no external call.
      - On failure: EXACTLY ONE of:
          fatal: set state.error    (run aborts → handle_error)
          partial: log + continue   (degrade; node still writes the named fallback value above)
    A node that touches an external system with NO external-calls row is REJECTED.
    A pure in-memory node (e.g. a router) states "External calls: none".
  - Behaviour: ONE sentence — the transformation SUMMARY only (inputs → output). The guard and
    I/O contract live in the table above, NOT in prose. No implementation line-by-line (src/).

WEAK vs STRONG (I/O & Guard table):
  weak  : Behaviour = "Calls the model and returns the answer." (no guard predicate, no named field)
  strong: Prompt inputs = `schema, question`; Output field = `sql`;
          Guard = `sql.strip().upper().startswith("SELECT") and ";" not in sql.rstrip(";")`;
          On guard fail = `fatal: set state.error`.

CLOSING RULE (gate-checkable, enumerable like the State cross-check):
  Every SC-N declared in vision.md MUST be served by at least one node's Serves cell. An SC-N
  with no serving node is a CRITICAL gap and is REJECTED. Conversely every Serves cite must
  resolve to a real SC-N (vision.md) / PN-ACn (delivery-plan.md) row — a dangling id is drift.
-->

### `node_<name>`

| Aspect | Value |
|--------|-------|
| Reads | <!-- State field names --> |
| Writes | <!-- State field names (include `error` if it can fail fatally) --> |
| Serves | <!-- SC-N (vision.md) · PN-ACn (delivery-plan.md)  /  internal: serves `node_<x>` by producing `<field>` --> |

**I/O & Guard**

| Aspect | Value |
|--------|-------|
| Prompt / data inputs | <!-- State fields fed in (LLM: prompt fields; DB/tool: call params) --> |
| Output field written | <!-- the single State field populated on success (must be in Writes) --> |
| Guard (predicate) | <!-- a Python boolean expression over state/output, e.g. `sql.strip().upper().startswith("SELECT")` — PROSE REJECTED --> |
| On guard fail | <!-- fatal: set state.error  /  partial: write `<named fallback value>` --> |

**External calls**

| System | Operation | Timeout | Retries (count, base_ms, cap_ms, jitter) | Idempotent? | Stub fallback | On failure |
|--------|-----------|---------|------------------------------------------|-------------|---------------|-----------|
| <!-- Gemini / DuckDB / none --> | <!-- e.g. NL→SQL completion (gemini-2.x, see architecture.md) --> | <!-- e.g. 30s --> | <!-- e.g. (0, –, –, n) or `no retry` --> | <!-- yes/no --> | <!-- exact value written in stub_mode, e.g. `sql="SELECT 1 AS stub"` --> | <!-- fatal: set state.error / partial: log + continue --> |

**Behaviour:** <!-- ONE sentence: inputs → transformation → output. Guard + I/O contract live in the tables above, not here. -->

---

<!-- Repeat the block above for EVERY functional node. Do NOT include handle_error/finalize here
     — those are specified in the next section. -->

---

## Edge Topology

<!--
FILL IN: a CONCRETE ASCII diagram of the compiled graph. NOT optional, NOT a placeholder comment.
The skeleton below is a LIVE fenced block, NOT a comment — you MUST overwrite it in place.
REQUIREMENTS:
  - START and END both appear.
  - Every node from the Nodes section appears, plus handle_error and finalize.
  - Every CONDITIONAL edge is drawn WITH its predicate inline, e.g.  ─(error)─►handle_error
    and  ─(ok)─►next_node . Show the branch labels, not a bare arrow.
  - The error route from EVERY fatal-capable node to handle_error is visible (a fan-in to
    handle_error is fine; show at least the representative edges).
  - finalize is the single success terminus before END.

HARD BAR (enumerable cross-check, same rigor as the State-field check):
  - Every node name in this diagram MUST appear VERBATIM in the Nodes section, and every
    Nodes-section node MUST appear here. A name present in one and not the other is REJECTED.
  - DO NOT ship the placeholder node names `node_first` / `node_second` / `node_route` /
    `node_tool`. A diagram still containing any of these literal names is REJECTED — they are
    scaffolding, not your graph.

Then a CONDITIONAL-EDGE TABLE enumerating each branch precisely.
-->

```
REPLACE THIS BLOCK with the real compiled graph. Example shape to overwrite (delete the
placeholder names — they MUST NOT survive into a filled spec):

START
  │
  ▼
node_first ──(state.error is not None)──► handle_error ──► END
  │ state.error is None
  ▼
node_second ──(state.error is not None)──► handle_error
  │ state.error is None
  ▼
node_route ──(state.next == "tool")──► node_tool ──► node_route   (loop)
  │ state.next == "done"
  ▼
finalize ──► END
```

<!-- FILL IN: every conditional edge as a row. Unconditional edges may be listed in prose under
     the diagram or as rows with Condition = "always". -->

| After node | Condition (predicate over state) | Goes to |
|------------|----------------------------------|---------|
| `node_<name>` | `state.error is not None` | `handle_error` |
| `node_<name>` | `state.error is None` | `<!-- next node -->` |
| `<!-- router node -->` | `<!-- e.g. state.next == "tool" -->` | `<!-- node -->` |
| `<!-- last functional node -->` | always | `finalize` |

---

## Error & Finalize Nodes

<!--
FILL IN: the two terminal-housekeeping nodes. Both MUST reference REAL audit_log columns from
spec/data-model.md (run_id, action, payload, duration_ms — whatever the actual schema names are;
do not invent columns). Cross-ref, do not redefine the audit_log schema here.
-->

### `node_handle_error`

| Aspect | Value |
|--------|-------|
| Reads | `error`, `run_id`, `session_id` <!-- + any context fields --> |
| Writes | <!-- run status / nothing in state; side-effect = audit row --> |
| Audit write | <!-- audit_log row: action=`<!-- e.g. 'error' -->`, payload=`<error text>`, duration_ms=<!-- elapsed --> (columns per data-model.md) --> |
| Terminates | routes unconditionally to `END` |

**Behaviour:** <!-- Records the failure with run_id context to audit_log, sets the run's terminal
status, and routes to END. MUST NEVER raise (it is the last line of defence). State exactly what
it persists and what the API surfaces to the caller (cross-ref the error response in spec/api.md). -->

### `node_finalize`

| Aspect | Value |
|--------|-------|
| Reads | <!-- the pipeline output fields that form the response --> |
| Writes | <!-- run status = success; assembles the response object --> |
| Audit write | <!-- audit_log row(s): action=`<!-- e.g. 'run' -->`, payload=`<!-- summary -->`, duration_ms=<!-- total run elapsed --> (columns per data-model.md) --> |
| Terminates | routes unconditionally to `END` |

**Response shape** (REQUIRED — `field: type` per line; MUST equal the success response body in
spec/api.md. A bare cross-ref with no field list here is REJECTED so a loose api.md cannot leave
the shape uninvented):

```
<!-- FILL IN, one field per line, e.g.:
sql: str            # the executed read-only SQL
rows: list[dict]    # query result, >= 0 rows
chart: dict | None  # plotly spec, None if not chartable
run_id: str         # mirrors audit_log.run_id
-->
```

**Behaviour:** <!-- ONE sentence: closes a successful run — writes the audit_log row(s) with
duration_ms, assembles the final response (shape above) from the pipeline outputs, routes to END. -->

### Acceptance criteria (EARS — finalize/error are observable via the audit log)

<!--
FILL IN: each criterion is ONE EARS sentence paired with an EXACT acceptance test. NOT
stub-passable: every criterion names a user-visible artefact with a quantity or named field
(an audit_log row WITH a non-null duration_ms; an error response WITH a message field), never a
bare 200 + empty body. Cite the SC each advances.

WEAK vs STRONG:
  weak  : "WHEN a run finishes, the system SHALL log it."  (stub-passable; no quantity, no field)
  strong: "WHEN a run completes successfully, node_finalize SHALL write exactly 1 audit_log row
           with action='run' and duration_ms >= 0."
-->

| # | EARS statement | Acceptance test (command / pytest node / assertion) | Serves |
|---|---------------|------------------------------------------------------|--------|
| AG-AC1 | `WHEN a run completes successfully, node_finalize SHALL write exactly 1 audit_log row with duration_ms >= 0 AND return a response containing every field named in the Response-shape block above.` | `<!-- e.g. pytest tests/test_graph.py::test_finalize_writes_audit -q  →  asserts 1 row, duration_ms is not None, AND set(response.keys()) == {declared response fields} -->` | SC-<!--N--> |
| AG-AC2 | `IF any node sets state.error, THEN node_handle_error SHALL write 1 audit_log row with action='error' and a non-empty payload, and the graph SHALL route to END without raising.` | `<!-- e.g. pytest tests/test_graph.py::test_error_path -q  →  asserts row action=='error', no exception escapes ainvoke -->` | SC-<!--N--> |
| AG-AC3 | `WHILE stub_mode is true (no API key), the agent SHALL complete a run end-to-end, each stubbed node SHALL write the EXACT deterministic Stub-fallback value declared in its external-calls row, and node_finalize SHALL still write its audit_log row.` | `<!-- e.g. APP_LLM_PROVIDER=stub pytest tests/test_graph.py::test_stub_run -q  →  asserts the named stub field equals its declared value (e.g. state["sql"] == "SELECT 1 AS stub"), response is populated, exactly 1 audit row -->` | SC-<!--N--> |

---

## Graph Assembly

<!--
FILL IN: Python pseudocode wiring nodes and edges EXACTLY as the real graph.py will. Use the
chosen framework's REAL API. For LangGraph: StateGraph / add_node / set_entry_point (or
add_edge(START, ...)) / add_conditional_edges / add_edge / compile. Cross-ref
harness/patterns/langgraph.md for the exact import paths and the no-reducer rule.

HARD BAR:
  - EVERY node and EVERY edge from the diagram appears here (including handle_error + finalize).
  - Conditional edges use a REAL predicate lambda referencing `state["error"]` (or state.error),
    e.g. lambda s: "handle_error" if s.get("error") else "next".
  - The real file MUST be ≤ 60 lines — keep this assembly tight; no node bodies inline.
-->

```python
# NOTE: the real src graph file MUST be <= 60 lines (assembly only; node bodies live elsewhere).
from langgraph.graph import START, END, StateGraph
# from <app>.agent.nodes import node_..., node_handle_error, node_finalize

g = StateGraph(AgentState)
# g.add_node("<name>", node_<name>)            # repeat for every functional node
# g.add_node("finalize", node_finalize)
# g.add_node("handle_error", node_handle_error)

# g.add_edge(START, "<entry node>")            # or g.set_entry_point("<entry node>")
# g.add_conditional_edges(
#     "<node>",
#     lambda s: "handle_error" if s.get("error") else "<next>",
#     {"handle_error": "handle_error", "<next>": "<next>"},
# )
# g.add_edge("<last functional node>", "finalize")
# g.add_edge("finalize", END)
# g.add_edge("handle_error", END)

# app = g.compile()                            # add checkpointer= only per the section below
```

---

## Concurrency & Checkpointing

<!--
FILL IN: pick EXACTLY ONE concurrency model and EXACTLY ONE checkpointing posture, each per
phase. No hedging — state the concrete decision and the condition that would change it.

CONCURRENCY — choose one and justify:
  (a) one run per session at a time — POST <run endpoint> returns 409 while a run is active
      (cite the 409 case in spec/api.md), OR
  (b) parallel nodes X and Y within a run because <they have no data dependency>.

CHECKPOINTING — choose one and state the trigger condition:
  none / AsyncSqliteSaver (langgraph-checkpoint-sqlite) / AsyncPostgresSaver. A Phase-1 stub or
  sub-second single-pass agent may legitimately be "no checkpointing" — but STATE IT EXPLICITLY,
  including which later phase introduces a saver and why (e.g. multi-step plans / HITL interrupt).
  Use the ASYNC saver if the stack is async (harness/patterns/langgraph.md).

DEGRADE PATHS: any node whose On-failure is `partial: log + continue` MUST name the EXACT usable
value it writes on degrade in its external-calls "On failure" / "On guard fail" cell (e.g.
`partial: write rows=[]`). "log + continue" with no named fallback value is REJECTED — degraded
behaviour must be specified, not left to the executor.
-->

| Aspect | Decision | Trigger to revisit |
|--------|----------|--------------------|
| Concurrency | <!-- one run per session (409 while active, see api.md) / parallel nodes X,Y because … --> | <!-- e.g. when run latency > N s --> |
| Checkpointing | <!-- none (sub-second single pass) / AsyncSqliteSaver / AsyncPostgresSaver --> | <!-- e.g. when multi-step plans or HITL interrupt land in Phase N --> |
| State persistence between steps | <!-- in-memory only / saver-backed (where) --> | <!-- --> |

<!-- FILL IN: per-phase posture so the upgrade is an in-place swap, not a rewrite. -->

| Phase | Concurrency model | Checkpointing | Notes |
|-------|-------------------|---------------|-------|
| Phase 1 | <!-- e.g. one run per session --> | <!-- e.g. none (stub agent, sub-second) --> | <!-- stub_mode banner visible; agent is single-node stub --> |
| Phase <!--N--> | <!-- --> | <!-- e.g. AsyncSqliteSaver --> | <!-- swaps in saver when multi-step loop introduced --> |

### Acceptance criteria (EARS)

<!-- FILL IN: EARS criteria for the concurrency/checkpointing contract, each with an exact test.
     NOT stub-passable — assert the 409 status / a resumed run reading prior state. -->

| # | EARS statement | Acceptance test | Serves |
|---|---------------|-----------------|--------|
| AG-AC4 | `IF a run is already active for a session, THEN POST <run endpoint> SHALL return HTTP 409 with an error body, not start a second run.` | `<!-- e.g. curl two concurrent POSTs → second returns 409 (cross-ref api.md error table) -->` | SC-<!--N--> |
| AG-AC5 | `WHERE checkpointing is enabled, WHEN a run resumes from a checkpoint, the graph SHALL read the prior step's state and not re-execute completed nodes.` | `<!-- e.g. pytest test_resume → asserts node_X ran once; or "N/A this phase — no checkpointer" -->` | SC-<!--N--> |
