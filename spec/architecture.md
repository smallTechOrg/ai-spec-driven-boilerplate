# Architecture

> **Placeholder.** The researcher fills every section thoroughly at intake — highly technical and exact, no vague prose.

This is a **structure spec**: it states contracts (WHAT the wiring is), not implementation
(HOW each function is written — that lives in `src/`). It is the single home for the
**pinned stack**, the **component topology**, the **environment-variable registry**, the
**deterministic startup sequence** (including the readiness rule), the **inter-component
contracts**, the **enumerated failure modes**, the **concurrency & retry policy**, and the
**observability contract**. An executor reads this file and knows the wiring without inventing
anything: writer model, lock timeout, backoff numbers, request-id format, and per-failure log
fields are all pinned here, not left to guess.

**One-fact-one-place anchors that live HERE and are referenced elsewhere:** the pinned
versions, the env-var names, the port numbers, the failure-mode list. The `/health` response
shape and the `stub_mode` flag live in [api.md](api.md) and are *referenced* here; the
`audit_log` columns live in [data-model.md](data-model.md) and are *referenced* here. Do not
re-define those — link to them.

<!-- FILL IN: if the project genuinely has no network surface (pure library / CLI), keep this
     file but say so at the top of Component Topology and collapse the diagram to the single
     process + its file I/O. Never delete the failure-mode or env-var sections. -->

---

## Stack (pinned)

<!-- FILL IN: every layer below MUST have a concrete version pin OR a floor with a reason in
     parentheses: ">=3.12 (floor: PEP 695 generics)". A bare "latest" is REJECTED. Each pinned
     library that has a harness usage-spec MUST link it inline in Rationale:
     "see harness/patterns/<lib>.md". Available specs as of writing: fastapi, google-genai,
     langchain-core, langgraph, nextjs, pydantic-settings, sqlalchemy-async. If a layer is
     genuinely absent (e.g. no frontend), the Choice cell is "none" and Rationale gives the
     one-line reason ("CLI-only; no browser surface"). -->

<!-- HARD BAR (gate-checked): every Rationale cell MUST end with a parenthesized trace id —
     either `(→ SC-N)` citing a Success Criterion in vision.md, or `(→ constraint: <name>)`
     citing a Hard Constraint row in vision.md. A Rationale with no parenthesized SC/constraint
     id is REJECTED — generic prose ("async + Pydantic v2") with no id does NOT pass. A "none"
     Choice still needs a one-line reason but is exempt from the trace id. -->

| Layer | Choice | Version pin | Rationale (MUST end with `(→ SC-N)` or `(→ constraint: <name>)`) |
|-------|--------|-------------|------------------------------------------------------------------|
| Language | <!-- e.g. Python --> | <!-- e.g. >=3.12 (floor: PEP 695 generics) --> | <!-- one line, ends with a trace id --> |
| Package manager | <!-- e.g. uv --> | <!-- e.g. >=0.5 (floor: workspace lockfile) --> | <!-- one line, ends with a trace id --> |
| Web framework | <!-- e.g. FastAPI / none — reason --> | <!-- e.g. 0.115.* --> | <!-- e.g. async + Pydantic v2; see harness/patterns/fastapi.md (→ SC-2) --> |
| Settings loader | <!-- e.g. pydantic-settings --> | <!-- e.g. 2.* --> | <!-- e.g. typed env; see harness/patterns/pydantic-settings.md (→ constraint: typed-config) --> |
| Agent framework | <!-- e.g. LangGraph / none — reason --> | <!-- e.g. 0.2.* / n/a --> | <!-- e.g. typed state graph; see harness/patterns/langgraph.md (→ SC-1) --> |
| Database | <!-- e.g. DuckDB / SQLite / none — reason --> | <!-- e.g. 1.1.* --> | <!-- columnar analytics vs relational (→ constraint: latency-budget) --> |
| ORM / DB driver | <!-- e.g. SQLAlchemy async / raw driver / none --> | <!-- e.g. 2.* --> | <!-- e.g. async sessions; see harness/patterns/sqlalchemy-async.md (→ SC-3) --> |
| Frontend | <!-- e.g. Next.js / none — reason --> | <!-- e.g. 14.* (App Router) --> | <!-- e.g. RSC + fetch; see harness/patterns/nextjs.md (→ SC-4) --> |
| LLM provider | <!-- e.g. google-genai / stub-only --> | <!-- e.g. 1.* --> | <!-- e.g. gemini-2.0-flash; stub fallback; see harness/patterns/google-genai.md (→ SC-5) --> |

<!-- FILL IN: add rows for any other pinned dependency that the executor must install at an
     exact version (charting lib, test runner, migration tool if used). Every row a real pin,
     every Rationale ends with a trace id. -->

**Weak vs strong (pin):**
- ❌ Weak — `| Web framework | FastAPI | latest | fast |` (no pin, no reason, no trace id).
- ❌ Weak — `| Web framework | FastAPI | 0.115.* | async + Pydantic v2 |` (pinned, but Rationale ends with no `(→ SC-N)` / `(→ constraint: …)` — REJECTED).
- ✅ Strong — `| Web framework | FastAPI | 0.115.* | async + Pydantic v2 validation for the /query contract; see harness/patterns/fastapi.md (→ SC-2) |`

---

## Component Topology

<!-- FILL IN: the ASCII (or mermaid) diagram below is REQUIRED — replace the placeholder, do
     NOT leave "TODO". Show EVERY process and external service as a node. Label EVERY edge with
     (a) its direction (arrow) and (b) its transport (token from the allowed set below).
     Include the listening port for every process that listens. Every node in the diagram MUST
     appear as a row in the table below, and every table row MUST appear in the diagram. -->

<!-- HARD BAR (gate-checked): every edge transport label MUST be one of the EXACT tokens —
     Allowed transport tokens: `HTTP/JSON` | `HTTPS` | `in-process` | `file I/O` | `WebSocket`
     | `stdin/stdout`. Any other label ("API call", "data", "connects to") is REJECTED. This
     mirrors the enumerated type-token list in api.md. -->

```
<!-- REPLACE THIS BLOCK. Example shape (delete and write the real one). Edge labels use ONLY
     the allowed transport tokens:

Browser ── Next.js (:3000)
   │  GET /api/*   (HTTP/JSON)
   ▼
FastAPI (:8001) ──in-process──► <agent/service> ──HTTPS──► <LLM provider> (<model>)
   │
   ▼ file I/O
<Database> (./data/app.db)

-->
```

<!-- FILL IN: one row per node above. Source path is the real dir the executor will create/edit. -->

<!-- HARD BAR (gate-checked): the Responsibility cell MUST be ONE sentence AND it MUST name the
     concrete artefact this component owns — a section of api.md (e.g. "§POST /query"), a node in
     agent-graph.md (e.g. "node_generate_sql"), a table in data-model.md (e.g. "audit_log"), or
     a screen in ui.md. A responsibility that names no concrete artefact ("runs the graph",
     "handles requests") is REJECTED — sentence-count is NOT the bar; content is. -->

| Component | Responsibility (one sentence, MUST name the artefact it owns) | Source path |
|-----------|--------------------------------------------------------------|-------------|
| <!-- e.g. Browser UI --> | <!-- renders the screens + four states in ui.md §Screens --> | <!-- e.g. frontend/ --> |
| <!-- e.g. API server --> | <!-- serves the endpoints in api.md §POST /query, §GET /health; validates each request body --> | <!-- e.g. src/api/ --> |
| <!-- e.g. Agent / service --> | <!-- runs the graph in agent-graph.md (node_generate_sql → node_execute → node_finalize) --> | <!-- e.g. src/agent/ --> |
| <!-- e.g. Persistence --> | <!-- stores the `dataset` and `audit_log` tables in data-model.md --> | <!-- e.g. src/db/ --> |
| <!-- e.g. LLM provider --> | <!-- serves the completion call in agent-graph.md node_generate_sql (or its stub) --> | <!-- external / src/llm/ --> |

**Weak vs strong (topology):**
- ❌ Weak — a diagram that lists boxes with no arrows and no transport labels ("FastAPI, DB, LLM").
- ❌ Weak — `| Agent | runs the graph in agent-graph.md | src/agent/ |` (one sentence, but names no concrete node — REJECTED).
- ✅ Strong — every arrow shows direction + an allowed transport token + port, and the table maps each box to one responsibility that NAMES the api.md section / agent-graph.md node / data-model.md table it owns, with no orphan on either side.

---

## Environment Variables

<!-- FILL IN: this is the SINGLE registry. Code reads ONLY vars listed here — a var read in code
     but absent from this table is drift and the analyser flags it. MUST include: the provider
     switch (e.g. APP_LLM_PROVIDER with its allowed set), EVERY API key var, and the DB path var.
     "Required" is yes / no / conditional — and a conditional MUST state its condition
     ("if provider=google"). Secret vars show the env-var NAME only, never a real value (use "—").
     Give a concrete non-secret default where one exists; never leave a blank cell. -->

| Var | Required | Default / example | Purpose / allowed values |
|-----|----------|-------------------|--------------------------|
| `<!-- APP_LLM_PROVIDER -->` | yes | `stub` | switches live LLM vs canned stub; one of {`stub`, `<!-- google -->`} |
| `<!-- APP_GEMINI_API_KEY -->` | conditional — if provider=`<!-- google -->` | — (secret) | LLM auth; never logged |
| `<!-- APP_DB_PATH -->` | no | `./data/app.db` | database file location |
| `<!-- APP_PORT -->` | no | `8001` | API listen port (matches topology diagram) |
| `<!-- APP_LOG_LEVEL -->` | no | `INFO` | log verbosity; one of {`DEBUG`,`INFO`,`WARNING`,`ERROR`} |
| `<!-- APP_REQUEST_TIMEOUT_S -->` | no | `30` | per-call ceiling; matches Inter-Component Contracts |

<!-- FILL IN: add a row for every other var the loader reads (frontend NEXT_PUBLIC_* base URL,
     CORS origins, model name override, eval threshold, etc.). Anything with a `*` in the name
     above must be replaced with the real prefix you choose; the prefix is fixed once chosen. -->

**Weak vs strong (env):**
- ❌ Weak — `| GEMINI_API_KEY | yes | AIzaSyD... | key |` (leaks a secret value; "yes" hides that stub mode needs no key).
- ✅ Strong — `| APP_GEMINI_API_KEY | conditional — if APP_LLM_PROVIDER=google | — (secret) | Gemini auth; never logged |`

---

## Startup Sequence

<!-- FILL IN: a NUMBERED list, each step an OBSERVABLE state transition. It MUST specify, by name:
       - the schema bootstrap mechanism: create_tables() in the web-framework lifespan, idempotent
         CREATE TABLE IF NOT EXISTS — explicitly "no migrations / no Alembic";
       - provider resolution from the provider switch var, and the REFUSE-TO-START condition when
         a required key for live mode is missing (named exception, non-zero exit);
       - the /health probe — its response shape is defined in api.md (DO NOT redefine it here):
         it returns the boolean `stub_mode` so the operator can confirm which mode is live;
       - the readiness rule: /health is NOT-ready (503) until create_tables() completes (see the
         readiness criterion below).
     Number the steps in true execution order. -->

<!-- HARD BAR (gate-checked): every numbered step that is EXTERNALLY OBSERVABLE (a probe could see
     it, or it emits a log line) MUST name its observable signal in `backticks` — the exact log
     line substring OR the probe + expected status (e.g. "logs `schema ready`", "GET /health → 503").
     A step that only describes a transition with no named signal is REJECTED for that step. -->

1. <!-- e.g. Process launch → settings loaded via pydantic-settings from env (see Env Variables); logs `settings loaded`. -->
2. <!-- e.g. Provider resolved from APP_LLM_PROVIDER; if `google` and key absent → raise ValueError, exit non-zero, refuse to serve; stderr contains `APP_GEMINI_API_KEY`. -->
3. <!-- e.g. Web-framework lifespan starts → create_tables() runs idempotent CREATE TABLE IF NOT EXISTS — NO migrations, NO Alembic; logs `schema ready`. -->
4. <!-- e.g. Server binds APP_PORT (default 8001) and is ready to serve; logs `listening on :8001`. -->
5. <!-- e.g. GET /health → 200 with `stub_mode` boolean (shape defined in api.md). Before step 3 completes, GET /health → 503. -->

**Acceptance criterion 1 (refuse-to-start, EARS — Unwanted):**
<!-- FILL IN one EARS sentence + an exact test. Replace PN-ACn with a REAL id that EXISTS in
     delivery-plan.md (e.g. P1-AC2) — a placeholder `PN-AC?` is REJECTED. Example: -->
> **P1-AC?** — IF `APP_LLM_PROVIDER=google` AND `APP_GEMINI_API_KEY` is unset, THEN the server SHALL refuse to start and exit non-zero with a named error. (→ SC-?)
> **Test:** `APP_LLM_PROVIDER=google uv run uvicorn src.api.main:app` exits non-zero and stderr contains `APP_GEMINI_API_KEY`.

**Acceptance criterion 2 (readiness-before-bootstrap, EARS — Unwanted) — REQUIRED:**
<!-- FILL IN: this criterion is MANDATORY (not optional). It pins that the process refuses traffic
     until the schema exists, so the not-ready behaviour is contract, not invented. Cite a REAL
     PN-ACn from delivery-plan.md. Example: -->
> **P1-AC?** — WHILE create_tables() has not completed, GET /health SHALL return 503 (not 200), so no request is served against an absent schema. (→ SC-?)
> **Test:** start the app with bootstrap delayed; assert `GET /health` returns 503 before `schema ready` is logged and 200 after.

**Weak vs strong (startup):**
- ❌ Weak — "the server starts up and connects to the database" (no order, no bootstrap mechanism, no refuse condition, no observable signal).
- ❌ Weak — a step "server is ready to serve" with no named log line or probe status (observability asserted, not enforced — REJECTED).
- ✅ Strong — the numbered list above where step 2 names the exception, exit code, and stderr substring; step 3 names the `schema ready` log line; and step 5 cites both the `stub_mode` field from api.md and the 503-before-bootstrap readiness behaviour.

---

## Inter-Component Contracts

<!-- FILL IN: ONE row per edge in the Component Topology diagram — no edge may be missing. Transport
     is one of the allowed tokens (same set as the topology diagram). Timeout is a concrete number in
     SECONDS (matches APP_REQUEST_TIMEOUT_S where applicable). "On failure" names a REAL action: an
     HTTP status returned, `state.error` set + which node it routes to, a status after retries.
     "Handle the error" / "log it" alone is REJECTED. -->

<!-- HARD BARS (gate-checked):
     1. Every on-failure action whose transport CAN fail (HTTP/JSON, HTTPS, file I/O, WebSocket)
        MUST have a matching row in Failure Modes below with a real detection mechanism. The
        analyser flags any on-failure action with no corresponding Failure Modes row — this is a
        MUST, not a SHOULD.
     2. The Retry column MUST state the retry policy as `(count, base_ms, cap_ms, jitter)` OR the
        literal `no retry`. A bare "retry ×3" is REJECTED — it names a count but not the backoff
        base/cap/jitter the executor would otherwise invent. Reference the shared policy in the
        Concurrency & Retry Policy subsection rather than re-deriving numbers per row. -->

| Caller | Callee | Transport | Timeout (s) | Retry policy `(count, base_ms, cap_ms, jitter)` or `no retry` | On failure (concrete) |
|--------|--------|-----------|-------------|---------------------------------------------------------------|------------------------|
| <!-- Browser --> | <!-- API --> | <!-- HTTP/JSON --> | <!-- 30 --> | <!-- no retry --> | <!-- error toast, keep user input, surface request id --> |
| <!-- API --> | <!-- Agent --> | <!-- in-process --> | <!-- 60 --> | <!-- no retry --> | <!-- 500 + request id logged; no partial write --> |
| <!-- Agent --> | <!-- LLM provider --> | <!-- HTTPS --> | <!-- 30 --> | <!-- (2, 250, 4000, yes) --> | <!-- set state.error; node routes to handle_error --> |
| <!-- API --> | <!-- Database --> | <!-- file I/O --> | <!-- 5 --> | <!-- (3, 100, 2000, no) --> | <!-- after retries exhausted → HTTP 503 --> |

**Weak vs strong (contract):**
- ❌ Weak — `| Agent | LLM | HTTPS | 30 | retry ×3 | handle error |` ("handle error" is not an action; "retry ×3" omits base/cap/jitter).
- ✅ Strong — `| Agent | Gemini | HTTPS | 30 | (2, 250, 4000, yes) | asyncio.wait_for; on timeout set state.error and route to handle_error node which emits the stub fallback (→ Failure Modes: LLM call timeout) |`

---

## Failure Modes

<!-- FILL IN: ENUMERATE the runtime failures. Each row needs a real DETECTION mechanism (a named
     exception type or an observable signal — a row with no detection mechanism is REJECTED) and a
     concrete RECOVERY. Cover at minimum: LLM timeout/error, malformed model output, DB
     unavailable/locked, missing key in live mode, and EVERY external-call failure shown as an edge
     in the topology / Inter-Component Contracts. -->

<!-- HARD BARS (gate-checked):
     1. Each Recovery cell MUST cite a PN-ACn (e.g. P1-AC4) that ACTUALLY EXISTS as a row id in
        delivery-plan.md. A placeholder `PN-AC?` / `P?-AC?` is REJECTED, and a cited id with no
        matching criterion in delivery-plan.md is drift and is REJECTED. The id is a real anchor.
     2. Every on-failure action in Inter-Component Contracts above whose transport can fail MUST
        appear here as a row — a contract on-failure with no detection mechanism here is REJECTED. -->

| Failure | Detection (named exception / observable signal) | Recovery (concrete → REAL PN-ACn in delivery-plan.md) |
|---------|------------------------------------------------|--------------------------------------------------------|
| <!-- LLM call timeout --> | <!-- asyncio.TimeoutError --> | <!-- state.error set; UI shows retryable error state (→ P1-AC4) --> |
| <!-- Malformed model output --> | <!-- pydantic.ValidationError / json.JSONDecodeError --> | <!-- return 422 + offending payload to audit log (→ P2-AC3) --> |
| <!-- DB unavailable / locked --> | <!-- OperationalError / "database is locked" --> | <!-- retry per policy then HTTP 503 (→ P3-AC?) --> |
| <!-- Missing key in live mode --> | <!-- startup check, ValueError --> | <!-- refuse to start with named error (→ P1-AC?) --> |
| <!-- Upstream non-2xx from provider --> | <!-- httpx.HTTPStatusError --> | <!-- map to 502; surface request id (→ P2-AC?) --> |

**Weak vs strong (failure):**
- ❌ Weak — `| LLM fails | sometimes | show error |` (no exception type, no recovery, no criterion).
- ❌ Weak — `| LLM call timeout | asyncio.TimeoutError | set state.error (→ PN-AC?) |` (placeholder id never resolves — REJECTED).
- ✅ Strong — `| LLM call timeout | asyncio.TimeoutError after APP_REQUEST_TIMEOUT_S | set state.error; handle_error node emits stub fallback; UI Error state shows "Try again" (→ P1-AC4) |` (P1-AC4 is a real row in delivery-plan.md).

---

## Concurrency & Retry Policy

<!-- FILL IN: this subsection is REQUIRED. It removes the per-cell reinvention of writer model,
     lock timeout, and backoff numbers that Inter-Component Contracts and Failure Modes reference.
     Fill EVERY row — a blank cell is REJECTED. If a value genuinely does not apply, write the
     literal `n/a` plus a one-line reason. -->

| Concern | Decision | Notes |
|---------|----------|-------|
| Writer model | <!-- e.g. single-writer (one serialized DB writer) / connection-pooled (N) --> | <!-- why; the DB-locked failure mode depends on this --> |
| Lock-acquire timeout (s) | <!-- e.g. 5 --> | <!-- how long a writer waits before the DB-locked Failure Mode fires --> |
| Max concurrent in-flight requests | <!-- e.g. 16 / unbounded — reason --> | <!-- ties to the concurrency envelope in vision.md Hard Constraints --> |
| Restart safety (idempotent process start) | <!-- e.g. a second start with a partially-written DB file → CREATE TABLE IF NOT EXISTS is a no-op; no truncation --> | <!-- state the behaviour on re-start; "schema only" is NOT enough --> |

**Standard retry policy** (referenced by Inter-Component Contracts + Failure Modes — define ONCE here):

<!-- FILL IN: state the default retry policy as concrete numbers so no cell re-derives them.
     Any edge that deviates states its own `(count, base_ms, cap_ms, jitter)` inline. -->

> Default: `(count, base_ms, cap_ms, jitter)` = <!-- e.g. (2, 250, 4000, yes) -->. Backoff is exponential `base_ms * 2^attempt` capped at `cap_ms`; jitter is full-jitter when `yes`. Non-idempotent calls use `no retry` unless explicitly listed.

**Weak vs strong (concurrency/retry):**
- ❌ Weak — "the DB handles concurrency" / "retries on failure" (no writer model, no lock timeout, no backoff numbers).
- ✅ Strong — `Writer model: single-writer; lock-acquire timeout 5 s → on exceed raise OperationalError (Failure Modes: DB locked). Default retry (3, 100, 2000, no).`

---

## Observability

<!-- FILL IN: this subsection is REQUIRED. It anchors the "surface request id" / "log it"
     phrasing used in the green examples above so the executor does not invent the log schema.
     Read and conform to [harness/patterns/observability.md](../harness/patterns/observability.md).
     Fill EVERY row — a blank cell is REJECTED. -->

| Aspect | Contract |
|--------|----------|
| Request-id format | <!-- e.g. UUIDv4 string, generated at the API edge if absent --> |
| Request-id propagation | <!-- which topology edges carry it (header `X-Request-Id` on HTTP/JSON; passed into agent state on in-process; included in every audit_log row in data-model.md) --> |
| Per-failure log fields | <!-- the EXACT fields logged on every Failure Modes row: request_id, failure name, exception type, the on-failure action taken; cite data-model.md `audit_log` columns where persisted --> |
| Log level source | <!-- APP_LOG_LEVEL (see Environment Variables) --> |

**Weak vs strong (observability):**
- ❌ Weak — "log errors with a request id" (no id format, no propagation path, no field list).
- ✅ Strong — `request_id = UUIDv4 set at API edge; propagated as X-Request-Id (HTTP/JSON) and into agent state (in-process); every failure logs {request_id, failure, exc_type, action} and persists request_id to audit_log (data-model.md). See harness/patterns/observability.md.`

---

## Phase Notes (architecture deltas per phase)

<!-- FILL IN: the topology above is the FULL target. State which components are REAL vs
     STUBBED-WITH-CORRECT-SHAPE per phase, and which contract a later phase swaps in place.
     Phase 1 is a shaped first release under a 30-minute build ceiling: the UI is PRESENT, the
     stub-mode banner is visible (see ui.md / api.md stub_mode), and data paths may be stubbed —
     but every stub keeps the real API/UI shape. A capability that would push a phase past its
     ceiling moves to a NAMED later phase, never gets dropped. The full phase plan + EARS
     acceptance criteria live in delivery-plan.md — this table is just the architectural delta. -->

<!-- HARD BAR (gate-checked): the "Contract frozen for later swap" cell MUST cite the EXACT
     section + anchor that holds the frozen shape — e.g. `api.md §POST /query → Response 200`,
     `data-model.md §audit_log`, `agent-graph.md node_finalize`. A bare phrase like "/query
     response shape" with no §section anchor is REJECTED. Each REAL component in a later phase
     that turns a prior stub real MUST point at the SAME anchor the earlier phase froze, so the
     upgrade is an in-place swap (shape identical, only the value source changes), not a rewrite. -->

| Phase | Components REAL | Components STUBBED (correct shape) | Contract frozen for later swap (MUST be §section + anchor) |
|-------|-----------------|-------------------------------------|-----------------------------------------------------------|
| <!-- P1 --> | <!-- UI + API + /health --> | <!-- agent (canned), DB (in-mem fixture) --> | <!-- api.md §POST /query → Response 200 --> |
| <!-- P2 --> | <!-- + agent live (same Response 200 shape) --> | <!-- DB still stubbed --> | <!-- data-model.md §audit_log --> |
| <!-- P3 --> | <!-- + DB live (audit_log now persisted) --> | <!-- — --> | <!-- — --> |

<!-- FILL IN: confirm the phase ordering is acyclic and matches the Inter-Phase Dependency Map in
     delivery-plan.md; a phase that turns a stub real MUST reference (by §anchor) the frozen stub
     contract it replaces so the upgrade is an in-place swap, not a rewrite. -->

**Weak vs strong (phase notes):**
- ❌ Weak — `| P1 | UI + API | agent (canned) | /query response shape |` (bare phrase, no §anchor — REJECTED).
- ✅ Strong — `| P1 | UI + API + /health | agent (canned), DB (in-mem fixture) | api.md §POST /query → Response 200 |`, and P2 turns the agent real against that SAME `api.md §POST /query → Response 200` anchor.
