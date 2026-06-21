# Data Model

> **Placeholder.** The researcher fills every section thoroughly at intake — highly technical and exact, no vague prose.

<!-- APPLICABILITY: this file is REQUIRED for any project that persists state (datasets,
     sessions, audit rows, agent runs). It is OPTIONAL only for a pure stateless
     pass-through service that writes nothing to disk — if so, delete this file AND remove
     the Database row from architecture.md Stack. Otherwise fill it completely.

     CROSS-REF CONTRACT (one fact, one place):
       - Engine + version + DB file path live in architecture.md Stack and the
         `<APP>_DB_PATH` env var. Restate them here ONCE in Storage Engine and link back.
       - audit_log columns live HERE (this file is their single home). api.md and
         agent-graph.md reference them by name; they do not redefine them.
       - Every `Created by` / `Updated by` / `Deleted by` cell names a real endpoint
         (api.md) or node (agent-graph.md). Do not invent code paths that do not exist there.
       - Every entity here that the API/agent reads or writes must trace to a phase in
         delivery-plan.md (a column or table introduced in Phase N is marked accordingly).
     Replace every <!-- FILL IN --> and every <APP>/<placeholder>. No blank cells:
     use [ASSUMPTION: value] for a default, [NEEDS CLARIFICATION: q] only for a genuinely
     schema-changing unknown. -->

---

## Storage Engine

<!-- FILL IN: Name the LOCAL engine and tie the choice to the workload in one sentence each.
     - DuckDB → columnar, vectorized; choose for analytical scans over uploaded tabular data,
       aggregations, GROUP BY, large CSV/Parquet ingestion.
     - SQLite → row-store, transactional; choose for relational metadata, many small
       point reads/writes, session/audit bookkeeping.
     If BOTH are used (common: DuckDB for data + SQLite "spine" for metadata), you MUST give
     the engine→tables mapping table below and say which file holds what.
     NO SERVER DB (no Postgres/MySQL/Mongo) — local file engine only.
     Engine name AND version MUST byte-match architecture.md Stack > Database.
     File path MUST equal the `<APP>_DB_PATH` default in architecture.md Environment variables. -->

| Property | Value | Source of truth |
|----------|-------|-----------------|
| Engine | <!-- FILL IN: DuckDB \| SQLite --> | architecture.md Stack > Database |
| Version pin | <!-- FILL IN: e.g. `1.1.*` (DuckDB) / `3.45.*` (SQLite) — MUST match Stack --> | architecture.md Stack > Database |
| DB file path | <!-- FILL IN: e.g. `./data/app.db` — MUST equal `<APP>_DB_PATH` default --> | architecture.md env var `<APP>_DB_PATH` |
| Bootstrap | `create_tables()` at FastAPI lifespan startup — **no migrations, no Alembic** | architecture.md Startup sequence step 1 |
| Driver | <!-- FILL IN: e.g. `duckdb` 1.1.* / `aiosqlite` 0.20.* / SQLAlchemy async — MUST match Stack --> | architecture.md Stack |
| Concurrency note | <!-- FILL IN: e.g. single-writer; DB-locked handling cross-ref architecture.md Failure modes (DB locked) --> | architecture.md Failure modes |

<!-- FILL IN (REQUIRED ONLY IF TWO ENGINES): one-line mapping of each engine to the tables
     it owns. Delete this block if a single engine holds everything. -->

| Engine / file | Tables it owns |
|---------------|----------------|
| <!-- FILL IN: DuckDB `./data/app.db` --> | <!-- FILL IN: dataset, query_result, ... (the columnar/data tables) --> |
| <!-- FILL IN: SQLite `./data/meta.db` --> | <!-- FILL IN: session, audit_log, agent_run (the metadata/transactional tables) --> |

**Why this engine (workload tie-in):** <!-- FILL IN: 1–2 sentences. e.g. "Uploaded datasets
are scanned analytically (aggregations, GROUP BY) so DuckDB's columnar engine fits; session
and audit bookkeeping are small point writes kept in the same file." Vague answers like
"it's lightweight" are rejected — name the access pattern. -->

> **Weak vs strong (do not write weak):**
> - Weak — *"DuckDB is fast and lightweight."* (no access pattern named — REJECTED).
> - Strong — *"Uploaded datasets are scanned with GROUP BY aggregations (api.md §POST /query → SQL `SELECT … GROUP BY`), so DuckDB's columnar engine fits; session/audit are point writes in a SQLite spine."* (names the workload AND the api.md/agent-graph.md site that drives it).

---

## Timestamps & Timezone

<!-- FILL IN (REQUIRED — never blank): one decision that governs EVERY TIMESTAMP column in
     this file, so per-column timezone guessing is impossible. State the exception explicitly
     if any column deviates. The latency ledger and every `created_at` depend on this. -->

- **All `TIMESTAMP` columns are stored in UTC.** `now()` resolves to `CURRENT_TIMESTAMP` in UTC (wall-clock, not monotonic). <!-- FILL IN: confirm verbatim, or state the exact exception (which column, why, and its zone). -->
- **Duration columns** (`*_ms`) are computed from a **monotonic** clock, not wall-clock differences. <!-- FILL IN: confirm or state the source clock. -->

---

## Indexes

<!-- FILL IN (REQUIRED — not optional): one row per NON-PK lookup path that an endpoint
     (api.md) or agent node (agent-graph.md) performs. The PK index is implicit; do NOT list it.
     GATE: every column that appears in a WHERE / JOIN / ORDER BY in api.md or agent-graph.md
     MUST have either a declared index row here OR an explicit
     `[ASSUMPTION: full-scan acceptable, < N rows]` with N stated. A hot lookup with neither
     is REJECTED — it is the difference between meeting and missing the latency criterion.
     Composite uniqueness (e.g. one active session per user) is declared here as a UNIQUE index. -->

| Index name | Table | Columns (in order) | Kind | Driven by (endpoint/node) |
|------------|-------|--------------------|------|---------------------------|
| <!-- FILL IN: ix_audit_session_time --> | <!-- FILL IN: audit_log --> | <!-- FILL IN: (session_id, created_at) --> | <!-- index / UNIQUE --> | <!-- FILL IN: GET /sessions/{id}/audit (api.md) --> |
| <!-- FILL IN: ix_query_session --> | <!-- FILL IN: query --> | <!-- FILL IN: (session_id) --> | <!-- index --> | <!-- FILL IN: node_load_history (agent-graph.md) --> |
| <!-- FILL IN: every other WHERE/JOIN/ORDER BY column path, or an [ASSUMPTION: full-scan acceptable, < N rows] line below --> | <!-- --> | <!-- --> | <!-- --> | <!-- --> |

<!-- FILL IN (use only if a hot path is deliberately unindexed):
     "[ASSUMPTION: <table>.<column> full-scan acceptable, < <N> rows] — justified by <reason>." -->

---

## Entities

<!-- FILL IN: one ### subsection per entity. You MUST cover EVERY entity any endpoint
     (api.md) or agent node (agent-graph.md) reads or writes — typically at minimum:
     session, dataset, the query/result entity, agent_run. If api.md mentions an entity
     not modelled here, the spec is incomplete.

     COLUMNS (every entity table uses this exact header — no row may omit a cell):
       Field | Type | Required | Default | Mutability | Constraint | Notes

     PER-ENTITY RULES (the technical bar — each is REJECTED if violated):
       1. One row per field, all seven columns filled. No cell may be blank or left as the
          literal `<!-- -->`. Use `—` only where a column is genuinely N/A and say why in Notes.
       2. Type is a CONCRETE ENGINE TYPE: TEXT, INTEGER, BIGINT, REAL/DOUBLE, BOOLEAN,
          TIMESTAMP, BLOB, JSON. NEVER `object`, `any`, `string-ish`, or a bare placeholder.
       3. Exactly one PK row per entity (Constraint = PK; say uuid4 / autoincrement).
       4. Every FK row: Constraint = `FK→<entity>.<field>` naming the EXACT target, and it
          MUST also appear in the ER diagram below.
       5. Every TIMESTAMP states its DEFAULT (DEFAULT now() / DEFAULT CURRENT_TIMESTAMP), and
          its timezone is UTC per the Timestamps & Timezone section — do not restate the zone.
       6. Use CHECK for enumerations and bounds (e.g. CHECK (row_count >= 0),
          CHECK (status IN ('pending','done','error'))).
       7. DEFAULT column is REQUIRED for every field, not just TIMESTAMPs. Write the literal
          default (e.g. `'pending'`, `0`, `false`, `now()`) OR `NO-DEFAULT`. A `NO-DEFAULT`
          NOT-NULL column MUST name in Notes the writer (endpoint/node) that always supplies it.
       8. Every numeric column states UNITS — either as a field-name suffix (`_ms`, `_bytes`,
          `_rows`, `_count`) or in Notes. For REAL/DOUBLE, also state precision/scale or an
          explicit `[ASSUMPTION: ...]`. A unitless number column is REJECTED.
       9. Every user-supplied TEXT column states a max length in Notes (e.g. "≤ 255 chars")
          OR `[ASSUMPTION: unbounded — <justification>]`. An unbounded user TEXT with no
          justification is REJECTED (it is a validation gap in api.md and a DoS surface).
      10. Mutability column is REQUIRED per field: `immutable` OR `mutable by:<endpoint/node>`.
          The Lifecycle "Updated by" cell is DERIVED from these — they must not contradict.
          Append-only entities have every non-PK field `immutable`.
      11. NULL has MEANING: every nullable (Required=no) field states in Notes what NULL means
          (e.g. "NULL = no dataset bound" vs "NULL = result pending"). A nullable field with
          no NULL-semantics note is REJECTED.
      12. UNIQUE TEXT columns state case/collation in Notes (e.g. "case-sensitive" /
          "NOCASE — 'Foo.csv' collides with 'foo.csv'"). Unstated collation on a UNIQUE TEXT
          column is REJECTED.
      13. JSON SUB-SCHEMA is MANDATORY: every JSON column (and every structured-TEXT column
          that holds a serialized object) MUST be followed by a fenced sub-schema block right
          under the entity table — `key: type [required|optional] [bounds]` per key. A bare
          `JSON` / `TEXT` for a structured field with no sub-schema block is REJECTED: an
          executor cannot write a parser/validator from `JSON` alone.
     Mark which phase introduces the entity/column in Notes when relevant
     (cross-ref delivery-plan.md), e.g. "Notes: added Phase 2".

> **Weak vs strong (do not write weak):**
> - Weak — `column_schema | JSON | yes | NO-DEFAULT | immutable | — | the schema` (a JSON blob with no inner contract — REJECTED).
> - Strong — `column_schema | JSON | yes | NO-DEFAULT (set by POST /datasets) | immutable | — | inferred at upload` **plus** the fenced sub-schema block below it naming each key's type and bounds. -->

### `<!-- FILL IN: session -->`

<!-- FILL IN: one sentence — what this entity represents and who creates it. -->

| Field | Type | Required | Default | Mutability | Constraint | Notes |
|-------|------|----------|---------|-----------|-----------|-------|
| id | TEXT | yes | NO-DEFAULT (set by POST /sessions) | immutable | PK (uuid4) | server-generated uuid4 |
| created_at | TIMESTAMP | yes | now() | immutable | — | UTC per Timestamps & Timezone |
| <!-- FILL IN: field --> | <!-- TEXT/INTEGER/... --> | <!-- yes/no --> | <!-- literal / NO-DEFAULT --> | <!-- immutable / mutable by:<ep> --> | <!-- PK/FK→x.y/UNIQUE/CHECK --> | <!-- units/NULL-meaning/max-len --> |

### `<!-- FILL IN: dataset -->`

<!-- FILL IN: one sentence — e.g. "A user-uploaded tabular file registered for querying." -->

| Field | Type | Required | Default | Mutability | Constraint | Notes |
|-------|------|----------|---------|-----------|-----------|-------|
| id | TEXT | yes | NO-DEFAULT (set by POST /datasets) | immutable | PK (uuid4) | server-generated uuid4 |
| name | TEXT | yes | NO-DEFAULT (from upload) | immutable | UNIQUE | original filename; ≤ 255 chars; <!-- FILL IN: case-sensitive? NOCASE? (rule 12) --> |
| row_count | INTEGER | yes | NO-DEFAULT (from ingest) | immutable | CHECK (row_count >= 0) | unit: rows |
| size_bytes | INTEGER | <!-- yes/no --> | NO-DEFAULT (from ingest) | immutable | CHECK (size_bytes >= 0) | unit: bytes; <!-- FILL IN: max upload cap or [ASSUMPTION] --> |
| <!-- FILL IN: column_schema --> | JSON | <!-- yes/no --> | NO-DEFAULT (inferred at upload) | immutable | — | inferred at upload — sub-schema block REQUIRED below (rule 13) |
| uploaded_at | TIMESTAMP | yes | now() | immutable | — | UTC per Timestamps & Timezone |

<!-- FILL IN (REQUIRED by rule 13 — sub-schema for the JSON `column_schema` column): -->

```
column_schema: array<object>   # one entry per column of the uploaded table
  └ object:
      name:  string  required  # source column header, ≤ 255 chars
      dtype: string  required  # one of: 'TEXT'|'INTEGER'|'DOUBLE'|'BOOLEAN'|'TIMESTAMP'
      nullable: boolean optional default true
```

### `<!-- FILL IN: query / agent_run -->`

<!-- FILL IN: one sentence. This is typically the row that ties a session + dataset to an
     executed question/result. It is usually APPEND-ONLY (never updated) — so every non-PK
     field is `immutable` (rule 10). -->

| Field | Type | Required | Default | Mutability | Constraint | Notes |
|-------|------|----------|---------|-----------|-----------|-------|
| id | TEXT | yes | NO-DEFAULT (set by writer below) | immutable | PK (uuid4) | server-generated uuid4 |
| session_id | TEXT | yes | NO-DEFAULT | immutable | FK→session.id | must appear in ER diagram |
| dataset_id | TEXT | <!-- yes/no --> | <!-- null / NO-DEFAULT --> | immutable | FK→dataset.id | must appear in ER diagram; <!-- FILL IN: NULL = ? (rule 11) --> |
| question | TEXT | <!-- yes/no --> | NO-DEFAULT | immutable | — | the NL prompt; <!-- FILL IN: max length (rule 9) --> |
| status | TEXT | yes | `'pending'` | mutable by:node_finalize (agent-graph.md) | CHECK (status IN ('pending','done','error')) | the one mutable field on an otherwise append-only row |
| created_at | TIMESTAMP | yes | now() | immutable | — | UTC per Timestamps & Timezone |
| <!-- FILL IN: field --> | <!-- type --> | <!-- yes/no --> | <!-- literal / NO-DEFAULT --> | <!-- immutable / mutable by:<node> --> | <!-- --> | <!-- units/NULL-meaning/max-len --> |

<!-- FILL IN: add further ### entity subsections until EVERY entity referenced by api.md
     and agent-graph.md is modelled here. Do not stop at three if the product has more. -->

---

## Relationships (ER)

<!-- FILL IN: a CONCRETE ER diagram (ASCII or mermaid). REQUIRED — "TODO"/placeholder fails.
     Every FK declared in Entities MUST appear here, and every relationship row below MUST
     correspond to exactly one FK in Entities (bidirectional cross-check — a dangling
     relationship or an undiagrammed FK is REJECTED). After the diagram, one sentence per
     relationship naming CARDINALITY (1:N / N:1 / 1:1) AND on-delete
     (CASCADE / RESTRICT / SET NULL). A relationship without on-delete is incomplete.
     RATIONALE RULE: the Rationale cell MUST state the CONSEQUENCE of the chosen on-delete on
     real data (what rows survive/vanish/orphan). A tautology like "because they relate" is
     REJECTED. Weak: "session owns queries." Strong: "CASCADE — deleting a session removes its
     queries so no query orphans a missing session_id FK." -->

```
<!-- FILL IN — ASCII example shape (replace with your real entities/cardinality):

session  1───N  query      (FK query.session_id → session.id)
dataset  1───N  query      (FK query.dataset_id → dataset.id)
session  1───N  audit_log  (FK audit_log.session_id → session.id)

   OR mermaid:

erDiagram
    session  ||--o{ query     : has
    dataset  ||--o{ query     : referenced_by
    session  ||--o{ audit_log : records
-->
```

| Relationship | Cardinality | On delete | Rationale (consequence on real data) |
|--------------|-------------|-----------|--------------------------------------|
| session → query | 1:N | <!-- CASCADE/RESTRICT/SET NULL --> | <!-- FILL IN: e.g. "CASCADE — removing a session deletes its queries so none orphans a missing session_id." --> |
| dataset → query | <!-- 1:N --> | <!-- CASCADE/RESTRICT/SET NULL --> | <!-- FILL IN: e.g. "RESTRICT — a dataset with queries cannot be dropped, preserving query provenance." --> |
| session → audit_log | <!-- 1:N --> | <!-- CASCADE/RESTRICT/SET NULL --> | <!-- FILL IN: state what survives/vanishes; tautologies REJECTED --> |
| <!-- FILL IN: every other FK pair declared in Entities --> | <!-- 1:N/N:1/1:1 --> | <!-- CASCADE/RESTRICT/SET NULL --> | <!-- FILL IN: consequence, not tautology --> |

---

## Audit & Observability Tables

<!-- FILL IN: the tables that make outcomes inspectable. `audit_log` is REQUIRED for any
     project with an agent / LLM / SQL surface — it backs the audit-log success criteria
     and the observability pattern (harness/patterns/observability.md). If a separate
     latency/run table exists (e.g. agent_run with duration_ms per node), model it too.
     This file is the SINGLE HOME of the audit_log column list; api.md and agent-graph.md
     reference these columns by name, they do not redefine them. -->

### `audit_log`

A row per model/SQL execution — the inspectable record of every agent action. Cross-ref [harness/patterns/observability.md](../harness/patterns/observability.md) (OTel GenAI attribute names) and the OTel redaction flag `TRACE_INCLUDE_SENSITIVE_DATA`.

| Field | Type | Required | Default | Mutability | Constraint | Notes |
|-------|------|----------|---------|-----------|-----------|-------|
| id | BIGINT | yes | autoincrement | immutable | PK autoincrement | — |
| session_id | TEXT | yes | NO-DEFAULT | immutable | FK→session.id | must appear in ER diagram |
| created_at | TIMESTAMP | yes | now() | immutable | — | UTC per Timestamps & Timezone |
| action | TEXT | yes | NO-DEFAULT | immutable | CHECK (action IN ('sql','llm')) | extend the enum if more action kinds exist |
| payload | TEXT | yes | NO-DEFAULT | immutable | — | the SQL text or the LLM prompt; <!-- FILL IN: max length (rule 9) -->; see Sensitive Fields |
| rows_affected | INTEGER | no | null | immutable | CHECK (rows_affected >= 0) | unit: rows; NULL = action is 'llm' (no rows) |
| duration_ms | INTEGER | yes | NO-DEFAULT | immutable | CHECK (duration_ms >= 0) | unit: ms (monotonic); backs the latency criterion |

**OTel token/cost columns — REQUIRED whenever architecture.md Stack lists an LLM provider** (drop ONLY if no model is in the stack; if present they are not optional):

| Field | Type | Required | Default | Mutability | Constraint | Notes (OTel attr) |
|-------|------|----------|---------|-----------|-----------|-------------------|
| model | TEXT | for `llm` rows | null | immutable | — | `gen_ai.request.model`; NULL = action is 'sql' |
| input_tokens | INTEGER | for `llm` rows | null | immutable | CHECK (input_tokens >= 0) | unit: tokens; `gen_ai.usage.input_tokens`; NULL for 'sql' |
| output_tokens | INTEGER | for `llm` rows | null | immutable | CHECK (output_tokens >= 0) | unit: tokens; `gen_ai.usage.output_tokens`; NULL for 'sql' |

**Write sites (every write MUST name a real code path):**

| Action value | Written by | Cross-ref |
|--------------|-----------|-----------|
| `sql` | <!-- FILL IN: e.g. agent node `node_execute_sql` --> | agent-graph.md |
| `llm` | <!-- FILL IN: e.g. agent node `node_generate_sql` / endpoint --> | agent-graph.md / api.md |

<!-- FILL IN (optional run-tracking table): if the agent records per-run timing/state
     beyond audit_log, model it here with the same column-table rigor. Delete if unused. -->

### Audit criteria (EARS + acceptance tests)

<!-- FILL IN: EARS criteria that are NOT stub-passable. Each must assert a row EXISTS with
     a populated named field and a quantity — an empty list + 200 must FAIL it. Both the
     Event (happy-path) AND the State-Driven (atomicity / failure-path) criteria below are
     REQUIRED, and each Acceptance-test cell MUST be a runnable reference (pytest node id or
     curl) carrying a parseable assertion (`assert <lhs> == <value>` / `assert <count> >= <n>`).
     A test cell left as prose or pointing at "see tests/" is REJECTED. -->

- **Criterion (Event):** WHEN the agent executes a query, the system SHALL append exactly one `audit_log` row whose `action='sql'`, `payload` is the executed SQL, and `duration_ms` is a non-null integer ≥ 0.
- **Acceptance test:** <!-- FILL IN: e.g. `pytest tests/test_audit.py::test_sql_logged` — asserts `SELECT count(*) FROM audit_log WHERE action='sql'` >= 1 AND latest row `duration_ms IS NOT NULL`. -->

- **Criterion (Atomicity — State-Driven):** WHILE recording an action, the system SHALL write the `audit_log` row in the SAME transaction as the action it records, so that a FAILED action leaves no `action='sql'` audit row (or leaves exactly one row with the corresponding `query.status='error'`). The audit write and the action commit or roll back together.
- **Acceptance test (failure path — REQUIRED):** <!-- FILL IN: e.g. `pytest tests/test_audit.py::test_failed_sql_no_orphan_row` — inject a SQL execution error, then assert `SELECT count(*) FROM audit_log WHERE action='sql' AND payload=<bad_sql>` == 0 (rolled back) OR == 1 with the paired query row `status == 'error'`. Asserting only the happy path is INSUFFICIENT. -->

> **Weak vs strong (do not write weak):**
> - Weak — *"the audit_log endpoint SHALL return 200"* (a stub returning `[]` passes — REJECTED).
> - Weak — a happy-path-only test (passes even if a failed action silently writes a half-row — REJECTED for the atomicity criterion).
> - Strong — *"WHEN a query runs, an audit_log row with action='sql' and duration_ms ≥ 0 SHALL exist"* AND *"a failed action leaves no orphan audit row"*, each with a runnable test asserting a count.

---

## Lifecycle & Retention

<!-- FILL IN: one row per entity from the Entities + Audit sections — none may be missing
     (gate cross-checks: the Entity count here MUST equal the number of ### entity subsections
     plus audit_log). `Created by` MUST name a real endpoint (api.md) or node (agent-graph.md).
     `Updated by` is DERIVED from the per-field Mutability column (rule 10): it lists EXACTLY
     the `mutable by:<…>` writers declared on that entity's fields, or `never (append-only)` if
     every non-PK field is immutable. A contradiction between this cell and the Mutability
     column is REJECTED. State the delete/retention rule explicitly — "persists until DB file
     deleted" is acceptable ONLY if written, never left implied. Note the phase that introduces
     a DELETE path if it is deferred (cross-ref delivery-plan.md). -->

| Entity | Created by | Updated by (derived from Mutability) | Deleted by / retention |
|--------|-----------|--------------------------------------|------------------------|
| session | <!-- FILL IN: e.g. POST /sessions --> | <!-- never / the mutable-by writers --> | <!-- FILL IN: e.g. persists until DB file deleted --> |
| dataset | <!-- FILL IN: e.g. POST /datasets --> | <!-- never (append-only) --> | <!-- FILL IN: e.g. DELETE /datasets/{id} (Phase 3); else persists --> |
| query | <!-- FILL IN: e.g. node_execute (agent-graph.md) --> | <!-- e.g. status mutable by:node_finalize --> | <!-- FILL IN: e.g. with session CASCADE --> |
| audit_log | <!-- FILL IN: write sites above --> | never (append-only) | <!-- FILL IN: e.g. with session CASCADE; no separate retention --> |
| <!-- FILL IN: every other entity --> | <!-- endpoint/node --> | <!-- never / mutable-by writers --> | <!-- delete path or retention --> |

---

## Sensitive Fields

<!-- FILL IN: every field holding PII, a secret, or a model key, and how each is protected.
     The API-KEY RULE IS MANDATORY: any LLM/provider key MUST appear as
     'env-only, never persisted, never logged'. If genuinely nothing sensitive persists,
     you must STILL state the API-key line and the "no PII persisted" line — never blank.
     Cross-ref the OTel redaction flag `TRACE_INCLUDE_SENSITIVE_DATA=false`
     (harness/patterns/observability.md) and secret-hygiene.md.

     CLASSIFICATION DECISION RULE (no guessing — REJECTED if violated):
       - For any column holding user-uploaded content of UNKNOWN shape at spec time (e.g.
         dataset cells, `audit_log.payload` containing user SQL/questions), Classification
         MUST be the MOST-RESTRICTIVE applicable: PII-unknown -> treat as PII — UNLESS the
         researcher documents in Protection why the ingest path provably cannot contain PII.
         A bare "low" with no justification on user-content columns is REJECTED.
       - Uploaded data AT REST MUST have an explicit protection statement: encryption-at-rest
         (yes/no + mechanism), local-only (never leaves the host), and the deletion path.
         "It's just a local file" with no deletion rule is REJECTED. -->

| Field | Entity / location | Classification | Protection (at rest, in transit, in logs/traces) |
|-------|-------------------|----------------|---------------------------------------------------|
| `<APP>_GEMINI_API_KEY` (or provider key) | env var only | secret | never persisted, never logged (cross-ref architecture.md env vars + secret-hygiene.md) |
| `audit_log.payload` | DB | <!-- FILL IN: PII-unknown→PII unless justified (decision rule) --> | <!-- FILL IN: e.g. not exported via API; redacted in traces when TRACE_INCLUDE_SENSITIVE_DATA=false --> |
| <!-- FILL IN: uploaded dataset content (cells) --> | <!-- DuckDB data file --> | <!-- PII-unknown→PII unless ingest provably cannot contain PII --> | <!-- FILL IN: at-rest (encrypted? local-only) + deletion path (DELETE /datasets/{id} / DB removal) --> |
| <!-- FILL IN: any other PII/secret column, or rely on the no-PII line below --> | <!-- location --> | <!-- PII/secret/none + justification --> | <!-- env-only/never-logged/encrypted/deletion-path --> |

<!-- FILL IN (use VERBATIM if nothing sensitive persists, in ADDITION to the API-key row above):
     "No PII or secrets persisted; API keys live only in env vars per architecture.md."
     This line does NOT excuse the uploaded-data-at-rest statement above when datasets persist. -->
