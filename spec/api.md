# API — Programmatic Contract

> **Placeholder.** The researcher fills every section thoroughly at intake — highly technical and exact, no vague prose.

<!-- WHEN TO DELETE THIS FILE: only if the product has NO programmatic surface at all
     (no HTTP, no WebSocket, no CLI). A library with a public Python API still has a
     surface — document it here as the CLI/call contract. If unsure, keep the file. -->

This document is the binding contract between callers (UI, tests, other services) and the
server. It is concrete enough that frontend and backend can be built IN PARALLEL against it
without further conversation. Every schema below is a real type contract, not a sketch.

Cross-references (one fact, one home):
- The `/health` shape and `stub_mode` flag are owned here (§Endpoints → `GET /health`,
  §Stub Mode Signalling) and must match [architecture.md](architecture.md) Startup Sequence.
- Port numbers are owned by [architecture.md](architecture.md) / [vision.md](vision.md) Hard
  Constraints — referenced, never redefined here.
- Success Criteria `SC-N` live in [vision.md](vision.md); per-phase criteria `PN-ACn` live in
  [delivery-plan.md](delivery-plan.md). Endpoints cite these by id, never restate them.
- EARS criteria referenced by endpoints are authored in [vision.md](vision.md) /
  [delivery-plan.md](delivery-plan.md); offline rules in [harness/rules/testing.md](../harness/rules/testing.md).

---

## Surface & Conventions

<!-- FILL IN: State the API style, the base URL, and EVERY cross-cutting convention that
     binds all endpoints. These conventions are NORMATIVE — an individual endpoint MAY NOT
     invent its own error shape, id format, or timestamp format. Fill the table; then paste
     the canonical error envelope as a real typed JSON block. -->

| Convention | Value | Notes |
|------------|-------|-------|
| API style | <!-- REST over HTTP / WebSocket / CLI / gRPC --> | <!-- one style is primary; if WS used for streaming, say which endpoints --> |
| Base URL | `http://localhost:8001` | Owned by architecture.md; do not redefine the port here. |
| Request content type | `application/json` | <!-- name any exception, e.g. multipart for file upload --> |
| Response content type | `application/json` | <!-- streaming endpoints: `text/event-stream` --> |
| Charset | `utf-8` | <!-- --> |
| Id format | <!-- `str (uuid4)` / `int >= 1` --> | One format for ALL resource ids unless a row gives a per-resource exception. |
| Timestamp format | `ISO-8601 UTC` (e.g. `2026-06-22T04:10:00Z`) | All `*_at` fields. Never epoch ints. |
| Pagination | <!-- none / `?limit:int&offset:int` / cursor --> | Forced choice — define the param types + envelope below, or state "no pagination". No "TBD". |
| Success status policy | reads: 2xx = success; **201 + `Location`** for creates; **202 + poll/stream** for async | Binds all endpoints — a create MUST NOT return 200; an endpoint MAY NOT invent its own success status. |
| Error envelope | See canonical block below | EVERY non-2xx body uses this exact shape. |
| CORS | <!-- allowed origins, e.g. `http://localhost:3000` --> | <!-- name the frontend origin from vision.md ports --> |

**Canonical error envelope (ALL non-2xx responses):**

```json
{
  "error": {
    "code": "string — SCREAMING_SNAKE machine code, stable, from each endpoint's matrix",
    "message": "string — human-readable, safe to surface in the UI toast"
  }
}
```

<!-- FILL IN — PAGINATION IS A FORCED CHOICE (no "TBD"). Write EXACTLY ONE of:
     (a) the typed envelope as a real block, e.g.:
         { "items": "array<Dataset> — page of results, element type named",
           "total": "int >= 0 — full count across all pages",
           "limit": "int >= 1 — page size echoed back",
           "offset": "int >= 0 — start index echoed back" }
         AND define the request param types in the convention table above (`?limit:int&offset:int`).
     (b) the EXACT sentence: "No pagination — list endpoints return the full set; bounded by [reason]."
         where [reason] names the cap that keeps the set bounded (e.g. "≤ N datasets per session").
     Weak (rejected): "Pagination TBD" / a blank cell / "we'll add paging later".
     Strong (required): one of (a) or (b) above — leaving an unbounded list with no param types is REJECTED. -->

| Acceptance criterion (EARS) | Acceptance test (RUNNABLE — pytest node or curl + assertion) |
|-----------------------------|--------------------------------------------------------------|
| `IF any endpoint returns a non-2xx status, THEN the body SHALL match the canonical error envelope with a non-empty `error.code` and a non-empty `error.message`.` | `<!-- e.g. tests/test_api.py::test_error_envelope_shape — POST /query with unknown dataset_id; assert json["error"]["code"] == "NO_DATASET" and json["error"]["message"] != "" -->` |

> Weak (rejected): "Errors return a JSON object." — stub-passable; an empty `{}` with 200 satisfies it.
> Strong (required): the EARS row above — names a non-2xx status, the exact envelope keys, AND a concrete `error.code` value asserted by a named test.
> The Acceptance-test cell MUST be a runnable pytest node or curl with a parseable assertion — an
> `<!-- e.g. -->` comment, blank, or "see tests/" is REJECTED (this rule binds EVERY EARS table in this file).

---

## Endpoints

<!-- FILL IN: ONE subsection per endpoint. For EACH endpoint you MUST provide, in order:
     1. A header line: `### METHOD /path  (→ Phase N)` — N is the phase it first ships in.
     2. Purpose: one sentence, observable outcome.
     3. Traces: the SC-N / PN-ACn id(s) this endpoint advances (≥1 required, and each MUST resolve).
     4. Request: a JSON block where EVERY field is `name: type [required|optional] [nullable] [constraint] — meaning`.
        No method body for GET.
     5. Response NNN: a JSON block where EVERY field is `name: type — meaning`.
     6. Error matrix: a table Status | code | Condition. `code` MUST appear in the canonical envelope.
     7. Stub shape (Phase 1): the exact canned body served when APP_LLM_PROVIDER=stub.
     8. Acceptance criteria (EARS) + a RUNNABLE acceptance test per row.
     Allowed type tokens: string | int | float | bool | ISO-8601 | array<T> | object{…} | null.
     FORBIDDEN: `<field>: <type>` placeholders, bare `Any`, bare `object` without a shape,
     or a field with no `— meaning`. Every list field states its element type and min count.

     HARD RULES — the analyser REJECTS the section if any is unmet:
     - TRACES RESOLVE: every id in Traces MUST be an existing row id in vision.md (SC-N) or
       delivery-plan.md (PN-ACn). A trace that does not resolve to a real row is drift and is
       REJECTED. Quote the cited criterion text inline so a wrong id is visible at review.
     - REQUEST CONTRACT: every request field MUST carry its grammar
       `name: type [required|optional] [nullable] [constraint] — meaning`, where `constraint`
       names the enum/allowed set, min/max length, numeric range, or id format. A field with no
       required-flag and no constraint is REJECTED.
         Weak (rejected):  `dataset_id: string — the dataset`           (no required-flag, no format)
         Strong (required): `dataset_id: string required (uuid4) — id of an existing dataset`
     - ERROR-MATRIX COVERAGE: any endpoint with a request body or path/query params MUST
       enumerate at least its 422 (validation failure) row and, if it resolves a resource by id,
       its 404 row — each with a precise trigger condition. A matrix with only 5xx rows is
       REJECTED for an input-taking endpoint.
     - SUCCESS STATUS: a create endpoint MUST return 201 with a `Location` header; an
       async/long-running endpoint MUST document 202 + the poll-or-stream contract. Do NOT
       default to 200 for creates.
     - SUCCESS BAR: the FIRST EARS row of every non-`/health` endpoint MUST assert a named
       success field carrying a quantity (`≥1` / non-empty / an exact value), never merely
       "returns 200".
     - STUB SHAPE: every endpoint MUST pin its Phase-1 stub body — same fields, same types as
       the live form, with real quantities (e.g. `rows` length ≥1). A stub that returns `{}` or
       omits fields is REJECTED (see §Stub Mode Signalling).
     - RUNNABLE TEST: every Acceptance-test cell MUST contain a runnable reference — a pytest
       node path (`tests/…::test_…`) OR a full `curl` — plus the asserted field and value as a
       parseable `assert <lhs> == <value>` or `assert <count> >= <n>`. A test cell left as an
       `<!-- e.g. -->` comment, blank, or a bare "see tests/" is REJECTED. -->

The table below is the index; each row is expanded in its own subsection. EVERY endpoint that
ships in ANY phase of [delivery-plan.md](delivery-plan.md) MUST appear here now (contract-first),
tagged with its phase. The `Traces` cell MUST cite a resolving SC-N / PN-ACn id, never `SC-?`.

| METHOD /path | Phase | Purpose (one line) | Traces (must resolve) |
|--------------|-------|--------------------|-----------------------|
| `GET /health` | Phase 1 | Liveness + stub/live signal | <!-- SC-N for stub-banner + PN-AC for readiness --> |
| <!-- e.g. POST /upload --> | <!-- Phase N --> | <!-- --> | <!-- SC-N / PN-ACn --> |
| <!-- e.g. POST /query --> | <!-- Phase N --> | <!-- --> | <!-- SC-N / PN-ACn --> |
| <!-- e.g. GET /datasets --> | <!-- Phase N --> | <!-- --> | <!-- SC-N / PN-ACn --> |

<!-- ===================== KEEP THIS ENDPOINT (always required) ===================== -->

### `GET /health`  (→ Phase 1)

**Purpose:** report liveness and whether the server is serving canned stub data or live data.

**Traces:** <!-- FILL IN: SC-N for the offline/stub-banner criterion + the PN-ACn for the
             readiness step. Each MUST resolve to a real row in vision.md / delivery-plan.md;
             quote the criterion text inline. -->

**Request:** none (no body, no query params).

**Response 200:**
```json
{
  "status": "string — literal \"ok\" while the process is serving",
  "stub_mode": "bool — true WHEN APP_LLM_PROVIDER=stub, else false"
}
```

<!-- This shape is NORMATIVE and MUST byte-for-byte match architecture.md Startup Sequence
     step "GET /health returns {\"status\": \"ok\", \"stub_mode\": true/false}". Do not add
     fields here without changing architecture.md in the same edit (one fact, one place). -->

**Error matrix:**

| Status | code | Condition |
|--------|------|-----------|
| <!-- 503 --> | <!-- code from envelope --> | <!-- e.g. readiness probe before create_tables() completes — cross-ref architecture.md Startup Sequence; or "none: /health never errors while the process is up" --> |

**Stub shape (Phase 1):** byte-identical to Response 200 with `stub_mode: true` —
`{"status":"ok","stub_mode":true}`. No network, no key. (Stub mode is `/health`'s normal Phase-1 state.)

| Acceptance criterion (EARS) | Acceptance test (RUNNABLE — pytest node or curl + assertion) |
|-----------------------------|--------------------------------------------------------------|
| `WHILE APP_LLM_PROVIDER=stub, GET /health SHALL return 200 with body {"status":"ok","stub_mode":true} and SHALL make no network call.` | `<!-- e.g. tests/test_health.py::test_health_stub_offline (ALLOW_MODEL_REQUESTS=False) — assert r.status_code == 200 and r.json() == {"status":"ok","stub_mode":True} -->` |

> Weak (rejected): "`/health` returns 200." — a bare 200 with empty body passes; says nothing about stub_mode.
> Strong (required): the EARS row above — asserts the exact body INCLUDING `stub_mode`, and the no-network guarantee.
> The Acceptance-test cell MUST be a runnable pytest node or curl with a parseable assertion — an
> `<!-- e.g. -->` comment, blank, or "see tests/" is REJECTED (same rule as §Endpoints).

<!-- ===================== TEMPLATE: copy per real endpoint ===================== -->

### `<!-- METHOD /path -->`  (→ Phase <!-- N -->)

**Purpose:** <!-- one sentence; observable outcome, not implementation -->

**Traces:** <!-- SC-N and/or PN-ACn id(s); ≥1 required; each MUST resolve to a real row.
             Quote the cited criterion inline, e.g. `SC-3 "p95 query latency ≤ 5 s"`. -->

**Request:** <!-- EVERY field: `name: type [required|optional] [nullable] [constraint] — meaning`.
                  `constraint` = enum/allowed set, min/max length, numeric range, or id format. -->
```json
{
  "<!-- field -->": "<!-- e.g. dataset_id: string required (uuid4) — id of an existing dataset -->",
  "<!-- field -->": "<!-- e.g. limit: int optional [1..500] (default 50) — max rows to return -->"
}
```
<!-- FORBIDDEN: `dataset_id: string — the dataset` (no required-flag, no constraint) is REJECTED.
     For multipart/file endpoints, document the form fields as a table instead:
     | part | type | required | constraint | meaning |
     | file | file (text/csv) | yes | ≤ 10 MB, UTF-8 | the dataset to ingest | -->

**Response 200:** <!-- swap to `Response 201` + a `Location` header line if this endpoint CREATES a
                       resource; document `Response 202` + the poll/stream contract if async. -->
```json
{
  "<!-- field -->": "<!-- type — meaning. EVERY field annotated; list fields name element type + min count -->"
}
```

**Error matrix:** <!-- An input-taking endpoint MUST list its 422 row; an endpoint that resolves a
                      resource by id MUST also list its 404 row. A matrix with only 5xx rows is REJECTED. -->

| Status | code | Condition |
|--------|------|-----------|
| <!-- 422 — REQUIRED if request has a body/params --> | <!-- BAD_INPUT --> | <!-- precise trigger, e.g. `limit` outside [1..500] --> |
| <!-- 404 — REQUIRED if resolving a resource by id --> | <!-- NO_RESOURCE --> | <!-- precise trigger, e.g. dataset_id not found --> |
| <!-- 500 --> | <!-- INTERNAL --> | <!-- unexpected failure; cross-ref architecture Failure modes --> |

**Stub shape (Phase 1):** <!-- The EXACT canned body served when APP_LLM_PROVIDER=stub: same
                              fields and types as Response 200 above, with real quantities (e.g.
                              `rows` length ≥1, a non-empty `sql`). Stubbed by VALUE, never by
                              omission. `{}` or a field-stripped body is REJECTED. -->
```json
{
  "<!-- field -->": "<!-- the deterministic canned value, shape-identical to the live response -->"
}
```

| Acceptance criterion (EARS) | Acceptance test (RUNNABLE — pytest node or curl + assertion) |
|-----------------------------|--------------------------------------------------------------|
| `WHEN [valid request], the endpoint SHALL return 200 with [named field carrying a quantity, e.g. rows length ≥ 1 / a non-empty sql string].` | `<!-- e.g. tests/test_query.py::test_query_returns_rows — assert r.status_code == 200 and len(r.json()["rows"]) >= 1 -->` |
| `IF [bad input named precisely], THEN the endpoint SHALL return [status] with error.code == "[CODE]".` | `<!-- e.g. tests/test_query.py::test_bad_dataset — assert r.status_code == 404 and r.json()["error"]["code"] == "NO_DATASET" -->` |

> Weak (rejected): "Returns a list of rows." — `{"rows": []}` + 200 passes.
> Strong (required, MANDATORY for the FIRST EARS row of every non-`/health` endpoint): "WHEN the
> query matches ≥1 record, `rows` SHALL contain ≥1 object each with the columns named in the SQL
> `SELECT`." — a first row that only asserts status 200 is REJECTED.

<!-- Repeat the block above for EVERY endpoint. Endpoints arriving in later phases are still
     documented here now (contract-first), tagged with their phase, so the UI can be built
     against frozen shapes. A later phase that turns a stubbed endpoint real MUST keep this
     exact request/response shape AND the same field set as its Stub shape above — only the
     VALUES become live (see Stub Mode Signalling). -->

---

## Authentication

<!-- FILL IN: State the scheme EXACTLY. If 'none for local demo', you MUST name the phase
     (or 'never (by design)') and cross-ref vision.md Non-Scope + delivery-plan.md. If a
     header/token is used, name the header and its exact format. No vague "auth TBD". -->

| Aspect | Value |
|--------|-------|
| Scheme | <!-- none (local demo) / API-key header / bearer (JWT) --> |
| Header name + format | <!-- e.g. `X-API-Key: <key>` / `Authorization: Bearer <jwt>` / n/a --> |
| Applies to | <!-- all endpoints / all except GET /health / n/a --> |
| Phase auth is introduced | <!-- "never (by design)" OR "Phase N — see delivery-plan.md" --> |
| Cross-ref | <!-- vision.md Non-Scope row that excludes/defers auth --> |

| Acceptance criterion (EARS) | Acceptance test (RUNNABLE — pytest node or curl + assertion) |
|-----------------------------|--------------------------------------------------------------|
| <!-- if scheme is none: `The server SHALL read no auth header and SHALL serve every endpoint to any local caller.` ; if a header: `IF a request omits the [header], THEN the server SHALL return 401 with error.code == "UNAUTHENTICATED".` --> | <!-- RUNNABLE: e.g. tests/test_auth.py::test_no_auth — assert r.status_code == 200 (scheme none); or ::test_missing_key — assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHENTICATED" (header scheme) --> |

> The Acceptance-test cell MUST be a runnable pytest node or curl with a parseable assertion — an
> `<!-- e.g. -->` comment, blank, or "see tests/" is REJECTED.

---

## Stub Mode Signalling

<!-- FILL IN: Exactly how the API tells callers it is serving canned data, so the UI can
     render the stub banner (see ui.md) and tests can assert offline behaviour. The
     stub_mode flag has ONE home: GET /health (above). State the deterministic + key-free
     + no-network guarantee. This is the Offline-stub HARD GATE. -->

| Aspect | Value |
|--------|-------|
| Signal field | `stub_mode: bool` in `GET /health` (defined once in §Endpoints) |
| Trigger | `APP_LLM_PROVIDER=stub` (env var owned by architecture.md) |
| Stub data property | Every stub response is deterministic AND shape-identical to its live counterpart (same fields, same types) — stubbed by VALUE, never by omission. |
| Network in stub mode | None. No outbound call, no API key required, on any endpoint. |
| Test enforcement | `ALLOW_MODEL_REQUESTS=False` in the test suite — any attempted network call fails the test. Cross-ref [harness/rules/testing.md](../harness/rules/testing.md). |
| UI consumer | `ui.md` stub banner reads `stub_mode` from `GET /health`. |

| Acceptance criterion (EARS) | Acceptance test (RUNNABLE — pytest node or curl + assertion) |
|-----------------------------|--------------------------------------------------------------|
| `WHILE APP_LLM_PROVIDER=stub, the entire API surface SHALL respond without a key or network, and each response SHALL carry the same named fields as its live form (e.g. /query SHALL return a non-empty sql string and rows length ≥ 1).` | `<!-- RUNNABLE: e.g. tests/test_stub.py::test_full_surface_offline (ALLOW_MODEL_REQUESTS=False, no API key set) — assert all responses 2xx and assert len(query.json()["rows"]) >= 1 and query.json()["sql"] != "" -->` |

> Weak (rejected): "In stub mode the server returns 200." — empty bodies pass; the UI cannot prove it is in stub mode.
> Strong (required): the EARS row above — `/health.stub_mode == true`, NO network (enforced by `ALLOW_MODEL_REQUESTS=False`), AND every stub response carries its real named fields with a quantity (e.g. `rows` ≥ 1).
> Each endpoint's exact canned body lives in its own §Endpoints "Stub shape (Phase 1)" block; this section is the surface-wide guarantee. A stub body of `{}` or one missing live fields is REJECTED.
> The Acceptance-test cell MUST be a runnable pytest node or curl with a parseable assertion — an
> `<!-- e.g. -->` comment, blank, or "see tests/" is REJECTED.

---

## Gaps & Assumptions

<!-- FILL IN: list every open contract question. Use [NEEDS CLARIFICATION: ...] only for
     genuinely contract-changing unknowns; [ASSUMPTION: value] for anything defaulted.
     Never leave a blank cell elsewhere — record the default here instead. -->

| Item | Type | Resolution / Owner |
|------|------|--------------------|
| <!-- e.g. id format across resources --> | <!-- ASSUMPTION / NEEDS CLARIFICATION --> | <!-- the value chosen, or the question + who answers --> |
