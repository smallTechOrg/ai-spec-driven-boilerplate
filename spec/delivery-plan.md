# Delivery Plan — Phased Build Contract & Embedded Roadmap

> **Placeholder.** The researcher fills every section thoroughly at intake — highly technical and exact, no vague prose.

<!--
  ROLE OF THIS FILE
  This is the build contract AND the roadmap in one. It defines the product as an ORDERED
  set of phases. Each phase has: exact scope (Real vs Stubbed), per-phase EARS acceptance
  criteria (PN-ACn) each tied to a concrete test, inter-phase dependencies, the applicable
  hard gates, and what it explicitly defers. There is NO separate ROADMAP.md — future scope
  IS the later phases here. There are NO FR/feature files — these spec docs ARE the spec.

  ONE FACT, ONE PLACE — this file owns the per-phase plan and the per-phase criteria (PN-ACn).
  It does NOT redefine facts owned elsewhere; it references them:
    - product Success Criteria (SC-N) + Non-Scope ...... spec/vision.md
    - stack choices + version pins ..................... spec/architecture.md
    - /health shape + stub_mode flag .................. spec/api.md (GET /health)
    - audit_log columns (e.g. duration_ms) ............ spec/data-model.md
    - screens, four states, UX bar .................... spec/ui.md
    - agent nodes / edges (if any) ................... spec/agent-graph.md
    - port numbers + build ceiling ................... spec/vision.md Hard Constraints
    - hard-gate definitions .......................... harness/rules/testing.md (The hard gates)

  TRACEABILITY LAW (bidirectional, MECHANICALLY enforced at the pre-code spec gate):
    - every SC-N in vision.md (the four labelled rows SC-CORE/SC-UX/SC-STUB/SC-FAIL AND every
      free SC-N) MUST be advanced by ≥1 phase below (coverage check)
    - every per-phase criterion (PN-ACn) below MUST cite a SC-N that RESOLVES to a real row in
      vision.md (→ SC-N) — a citation that does not resolve is drift and is REJECTED
    - an SC with no phase, or a phase criterion with no SC, is INCOMPLETE → gate fails
    - the two checks above are NOT prose assertions: they are filled and self-checked in the
      § Traceability Ledger at the bottom of this file (SC→Phases and PN-ACn→SC matrices).
      A prose "coverage looks complete" is not acceptable evidence; the ledger tables are.

  STUB-IMMUNITY LAW: no acceptance criterion below may be satisfied by a stub returning an
  empty list + 200. Each names a USER-VISIBLE ARTEFACT with a QUANTITY or a NAMED TYPED FIELD
  (row_count ≥ 1; a Plotly chart with axis labels + tooltips; an audit_log row with duration_ms).

  THE THREE COORDINATION FILES (do not confuse them):
    - THIS file (spec/delivery-plan.md) = the DURABLE phase roadmap. Ordered phases, per-phase
      EARS criteria (PN-ACn), inter-phase dependencies. Edited ONLY on a real spec change.
      It carries the phasing; there is NO separate ROADMAP.md and NO FR/feature files.
    - logs/PLAN.md = the LIVE coordination hub for the CURRENT phase (Step DAG + Progress
      Tracker + Phase Acceptance), rewritten whole by the planner at each phase start. It
      carries NO durable requirements — those live here. Do NOT copy PN-ACn definitions there.
    - logs/sessions/<timestamped>.md = the narrative log + Latency Ledger only.
-->

<!--
  EARS FORMS (every PN-ACn EARS cell MUST be EXACTLY ONE of these, with a quantity):
    - Ubiquitous:  "The <system> SHALL <response> <quantity>."
    - Event:       "WHEN <trigger>, the <system> SHALL <response> <quantity>."
    - State:       "WHILE <state>, the <system> SHALL <response> <quantity>."
    - Unwanted:    "IF <trigger/condition>, THEN the <system> SHALL <response/recovery>."
    - Optional:    "WHERE <feature is present>, the <system> SHALL <response> <quantity>."
  An EARS cell with no SHALL, or with two stitched clauses, or with no quantity (for the
  non-Unwanted forms), is REJECTED. The Unwanted form's quantity is the named error code/state.
-->

---

## Phasing Model

<!-- The phasing rules are NORMATIVE in [harness/rules/non-negotiables.md](../harness/rules/non-negotiables.md)
     (non-negotiable: "one phase = one user-testable increment; parallel steps inside"). DO NOT
     restate them verbatim here — a copied boilerplate table is pure decoration and inflates the
     appearance of thoroughness without committing to anything about THIS product.

     FILL IN INSTEAD: for each rule below, add ONE project-specific sentence in the "How it binds
     THIS product" column that names a concrete artefact of this build (a screen, an endpoint, a
     stub contract, a phase number). A cell that merely re-states the rule, or names no concrete
     artefact, is REJECTED. The rule text in column 2 is fixed (reference, not to edit). -->

A phase is the smallest slice of this product a user can open and **feel**. The normative rules
(owned by non-negotiables) and how each binds THIS product:

| # | Rule (normative — do not edit) | How it binds THIS product (REQUIRED — name a concrete artefact) |
|---|--------------------------------|------------------------------------------------------------------|
| 1 | A phase is a **vertically-sliced, user-testable increment** — it cuts UI → API → data → agent for its slice. NEVER a horizontal layer (no "the database phase"). | <!-- e.g. "Phase 1 cuts the upload screen (ui.md §Upload) → POST /query stub (api.md) → audit_log write (data-model.md)." — name the actual slice. --> |
| 2 | **Phase 1 ≤ 30 min build** (hard ceiling from [vision.md](vision.md) Hard Constraints) and is a *shaped first release*: the **UI is present even if every data path is stubbed**, stub-mode banner visible ([ui.md](ui.md) Stub-Mode Banner). | <!-- e.g. "Phase 1 ships the full shell (ui.md §Shell) with POST /query stubbed; nothing UI is omitted." --> |
| 3 | A phase is **Done** only when ALL hold: (a) every PN-ACn passes its named test; (b) the applicable **hard gates** are green ([harness/rules/testing.md](../harness/rules/testing.md)); (c) the **user explicitly accepts** the phase (the one user-acceptance boundary). | <!-- e.g. "Phase 1 Done = P1-AC1..P1-AC4 pass + the 8 P1 gates green + user accepts." --> |
| 4 | **No scope is dropped.** A capability past the ceiling moves to a named **later phase in THIS file** — never a separate ROADMAP, never silently cut. Disposition is a phase number here or `never — reason`. | <!-- e.g. "Real NL→SQL is deferred to Phase 2; nothing is cut — see § Explicitly Deferred." --> |
| 5 | Phases form an **acyclic dependency graph** (§ Inter-Phase Dependency Map). A phase cannot start until its dependency phase(s) are user-accepted and any contract it builds behind is frozen. | <!-- e.g. "Phase 2 waits on P1 accepted + POST /query shape frozen (api.md §POST /query)." --> |
| 6 | The phase that turns an earlier **stub** real must **reference the stub contract it replaces** ([api.md](api.md) Stub Mode Signalling) — an in-place swap, not a rewrite. | <!-- e.g. "Phase 2 replaces the POST /query stub; response schema byte-identical, only values change." --> |

---

## Phase Overview

<!-- FILL IN: the at-a-glance arc — ONE ROW PER PHASE. This is the roadmap view.
     RULES:
       - "Theme" is ONE line naming a USER-FEELABLE CAPABILITY, not a layer and not an
         adjective. A vague theme ("better answers", "improved UX", "more polish") is REJECTED:
         the theme MUST name the concrete thing the user can DO that they could not before
         (a verb + an object), e.g. "Ask a question and get a real model-generated answer".
       - "Advances SCs" cites SC-N ids from vision.md (including the labelled SC-CORE/SC-UX/
         SC-STUB/SC-FAIL). Every SC-N in vision.md MUST appear in at least one row — this is
         NOT eyeballed here; it is proven in the § Traceability Ledger (SC→Phases matrix).
       - "Depends on" forms a DAG (no cycles). Phase 1 depends on "—".
       - "Est. build" is REQUIRED for EVERY phase, not just Phase 1. State a number AND, in the
         same cell, the ONE capability that would breach the ceiling if added (forcing it into a
         deferral row). An estimate with no breach-capability named is decoration → REJECTED.
         Phase 1's number MUST be ≤ 30 min (the vision.md ceiling). -->

| Phase | Theme (verb + object; capability not layer) | Advances SCs | Depends on | Est. build (number + breach-capability) |
|-------|---------------------------------------------|--------------|------------|------------------------------------------|
| 1 | <!-- e.g. Open the shell, upload a file, get a stubbed-but-shaped answer + chart --> | <!-- e.g. SC-CORE, SC-STUB, SC-FAIL --> | — | <!-- e.g. ≤ 30 min (hard ceiling); adding real NL→SQL would breach → Phase 2 --> |
| 2 | <!-- e.g. Ask a question and get a real model-generated answer over your data --> | <!-- e.g. SC-CORE, SC-UX --> | <!-- 1 user-accepted --> | <!-- e.g. ~40 min; adding saved dashboards would breach → Phase 3 --> |
| 3 | <!-- e.g. Save, list, and delete datasets across sessions --> | <!-- e.g. SC-N --> | <!-- 2 user-accepted --> | <!-- e.g. ~40 min; adding multi-user auth would breach → never --> |
| <!-- N: add rows until every SC-N in vision.md is advanced by ≥1 phase (verify in the ledger) --> | | | | |

<!-- Do NOT write a prose "coverage looks complete" here. Coverage is PROVEN in the
     § Traceability Ledger below (SC→Phases). Any SC-N not appearing there is
     [NEEDS CLARIFICATION: which phase advances SC-N?] and BLOCKS the gate. -->

---

## Phase 1 — Shaped First Release

<!-- FILL IN: the fullest spec of Phase 1. Phase 1 is genuinely FEEL-ABLE end to end:
     the user opens a browser, sees the shell with the stub banner, performs the core
     interaction, and gets a SHAPE-CORRECT (stubbed) result. It MUST fit the ≤ 30 min ceiling.
     This subsection has FIVE mandatory parts (a)–(e) below — none may be omitted. -->

**Goal (verbatim from [vision.md](vision.md) "In one sentence"):**
<!-- FILL IN: quote the single-sentence product statement from vision.md, then state which
     parts are REAL in Phase 1 and which are STUBBED. One sentence each. -->
> _<quoted product sentence>_ — in Phase 1, <X is real; Y is stubbed-with-correct-shape>.

**Build estimate:** <!-- REQUIRED: state a number ≤ 30 min, e.g. "≤ 30 min (hard ceiling)". -->

### (a) In-scope — Real vs Stubbed

<!-- FILL IN: ONE ROW PER CAPABILITY in Phase 1. Every capability is either "Real" or
     "Stubbed (correct shape)". The UI rows MUST be present and Real-as-shell even when their
     data is stubbed — OMITTING the UI is not allowed (stub deeply, never by omission).
     "Why" states why it is real now or deferred-but-shaped. Every "Stubbed" row MUST name
     (1) the later phase that makes it real AND (2) the FROZEN CONTRACT it leaves behind — the
     exact api.md/ui.md section+anchor whose SHAPE will not change when the value goes real
     (e.g. "api.md §POST /query → Response 200 — schema byte-identical at swap; only values
     change"). A "Stubbed" row that names no frozen contract anchor is REJECTED. -->

| Capability | Real or Stubbed (correct shape) | Why + frozen contract (real now / shaped-but-deferred → Phase N, anchor) |
|------------|---------------------------------|--------------------------------------------------------------------------|
| <!-- e.g. Visible app shell + nav + four-state screens --> | <!-- Real (shell) --> | <!-- user must feel the product on first open --> |
| <!-- e.g. Stub-mode banner --> | <!-- Real --> | <!-- Stub-banner hard gate; ui.md Stub-Mode Banner --> |
| <!-- e.g. File upload + sidebar listing --> | <!-- Real / Stubbed --> | <!-- --> |
| <!-- e.g. Core answer (table + chart) --> | <!-- Stubbed (deterministic, real shape) --> | <!-- real model → Phase 2; FROZEN: api.md §POST /query → Response 200 schema byte-identical at swap, only values change --> |
| <!-- e.g. GET /health with stub_mode --> | <!-- Real --> | <!-- api.md §GET /health --> |
| <!-- add one row per capability; no UI omitted; every Stubbed row names its frozen anchor --> | | |

### (b) Golden Path Demo Script

<!-- FILL IN: a NUMBERED, user-terms walkthrough that runs end-to-end with NO explanation
     needed. It MUST include the step where the stub banner is visible, and MUST name the
     concrete artefact the user sees at each step (a filename, a row count, a chart). This is
     the script the Golden-path smoke + Live-UI hard gates execute. Replace every <...>. -->

```
1. Run <exact start command, e.g. `make dev`> — backend on :8001, frontend on :3000.
2. Open http://localhost:3000 — the shell renders; a full-width banner reads
   "STUB MODE — responses are canned, not real AI output" (verbatim; ui.md Stub-Mode Banner).
3. <core setup action, e.g. upload sample.csv> — the sidebar shows "<name> · <N> rows" (N ≥ 1).
4. <core ask action, e.g. type "top 5 by revenue" and submit> — a progress indicator shows.
5. A <sortable Markdown/GFM table with its row count> AND an <interactive Plotly chart with
   axis labels + tooltips + PNG-download> render (stubbed but shape-correct).
6. <follow-up, e.g. click a suggestion chip> — input fills and auto-submits a new stubbed answer.
```

<!-- A demo that ends at "a 200 is returned" is REJECTED — the script must end on a
     user-visible artefact with a quantity (row count, chart with labels). -->

### (c) Acceptance Criteria (EARS)

<!-- FILL IN: ONE ROW PER CRITERION, ids P1-AC1, P1-AC2, … FIVE columns, none droppable.

     EARS column — EXACTLY ONE EARS form (see EARS FORMS at top of file) WITH a QUANTITY. The
       quantity is a number/threshold/named-field for the non-Unwanted forms, or a named error
       code/state for the Unwanted form. A cell with no SHALL, two stitched clauses, or no
       quantity is REJECTED.
     Fixture + expected value column (REQUIRED) — the EXACT test data AND the EXACT asserted
       value, not "a known answer". Name the fixture FILE, its row count, and the literal
       expected number/string. "row count ≥ 1" alone is the FLOOR and is too weak on its own —
       pair it with the exact expected value so a wrong-but-non-empty answer FAILS.
     Acceptance test column — an EXACT, RUNNABLE proof: a full curl, a pytest node id
       (path::test_name), or a numbered UI click sequence, WITH the asserted-on string/number in
       `assert <lhs> == <value>` / `assert <count> >= <n>` form. A test cell that is a comment,
       blank, prose ("runs the query"), or "see tests/" is REJECTED — it must be executable.
     → SC column — cites a SC-N that EXISTS in vision.md (resolved in the ledger).

     MANDATORY coverage for Phase 1 (each MUST be a row below; a missing one fails the gate):
       - the visible stub banner (verbatim string asserted in rendered DOM)
       - the offline-stub contract (no key, no network — api.md Stub Mode Signalling)
       - the core stubbed answer rendered as a real UI artefact (table row count ≥ 1 AND/OR
         a Plotly chart with axis labels) — shape-correct even though data is stubbed
       - at least ONE Unwanted-behaviour (IF…THEN) failure criterion that names an error code
         from § Error Codes Introduced and states the recovery
     NO criterion may be satisfiable by empty-list + 200. -->

| id | EARS statement (one EARS form, with a quantity) | Fixture + expected value (file, count, literal answer) | Acceptance test (curl / pytest node / UI clicks + `assert`) | → SC |
|----|------------------------------------------------|--------------------------------------------------------|--------------------------------------------------------------|------|
| P1-AC1 | <!-- e.g. WHILE stub_mode is true, the app SHALL display a full-width top banner reading exactly `STUB MODE — responses are canned, not real AI output` on first paint of every screen. --> | <!-- e.g. n/a — static banner; expected literal = the verbatim banner string. --> | <!-- e.g. start frontend in stub mode; `assert "STUB MODE — responses are canned, not real AI output" in dom` (Live-UI gate). --> | <!-- SC-? --> |
| P1-AC2 | <!-- e.g. WHILE APP_LLM_PROVIDER=stub, GET /health SHALL return 200 `{"status":"ok","stub_mode":true}` and make no network call. --> | <!-- e.g. no fixture; expected body == {"status":"ok","stub_mode":true}, status == 200. --> | <!-- e.g. pytest tests/test_health.py::test_health_stub_offline — `assert r.json()=={"status":"ok","stub_mode":true}` with ALLOW_MODEL_REQUESTS=False. --> | <!-- SC-? --> |
| P1-AC3 | <!-- e.g. WHEN a question is asked in stub mode, a GFM table (≥1 row, row count shown) AND a Plotly chart with both axis labels SHALL render. --> | <!-- e.g. fixture sample.csv (100 rows); ask "top 5 by revenue" → stub returns exactly 5 rows [Widget A … Widget E]; header reads "5 rows". --> | <!-- e.g. UI: submit "top 5"; `assert header_text == "5 rows"` AND `assert axis_title_count >= 2` AND `.modebar` present. --> | <!-- SC-? (shape) --> |
| P1-AC4 | <!-- Unwanted: e.g. IF the upload is not a valid CSV, THEN the UI SHALL show an inline error "Unsupported file" and the prior state SHALL remain visible. --> | <!-- e.g. fixture broken.png; expected toast literal == "Unsupported file"; sidebar row count unchanged. --> | <!-- e.g. upload broken.png; `assert toast_text == "Unsupported file"` AND `assert sidebar_rows == before`. --> | <!-- SC-? --> |
| <!-- add rows until the four mandatory coverage items above are all met --> | | | | |

> **Weak vs Strong (do not ship Weak):**
> - **Weak EARS** (REJECTED — stub-passable): "WHEN a question is asked, the system SHALL return a result." — `{"rows": []}` + 200 satisfies it.
> - **Strong EARS** (accepted): P1-AC3 above — names a table with a visible row count ≥ 1 AND a chart with axis labels; an empty-200 cannot pass.
> - **Weak test** (REJECTED — empty assertion): "pytest tests/test_query.py::test_top5 — runs the query." — names a node, asserts nothing.
> - **Strong test** (accepted): "pytest tests/test_query.py::test_top5 — `assert r.json()['row_count'] == 5 and r.json()['rows'][0]['name'] == 'Widget A'`." — a wrong answer fails.
> - **Weak fixture** (REJECTED): "a known-answer query → ≥1 row." — any non-empty result passes.
> - **Strong fixture** (accepted): "sample.csv (100 rows); top-5-by-revenue → rows == [Widget A, B, C, D, E], row_count == 5." — a wrong-but-non-empty answer fails.

### (d) Applicable hard gates (Phase 1)

<!-- FILL IN: tick the gates that apply to Phase 1 and name the exact command/assert per row.
     Gate definitions are owned by harness/rules/testing.md — reference, do not redefine.
     For Phase 1 (UI present, stubbed): Offline-stub, Live-server, Live-UI, Stub-banner,
     Golden-path smoke, and README current ALWAYS apply. Production-driver applies IF a DB is
     present in Phase 1. Eval-threshold does NOT apply yet (no live agent behaviour). -->

| Hard gate | Applies in P1? | Exact assertion for this phase |
|-----------|----------------|--------------------------------|
| Offline stub | <!-- yes --> | <!-- e.g. `APP_LLM_PROVIDER=stub uv run pytest` exits 0, no network (ALLOW_MODEL_REQUESTS=False) --> |
| Live-server (backend) | <!-- yes --> | <!-- e.g. `python -m src` starts; `curl :8001/health` → 200 with stub_mode:true --> |
| Live-UI (frontend) | <!-- yes --> | <!-- e.g. `npm run start`; `curl :3000/` → 200 with banner string in DOM --> |
| Stub banner | <!-- yes --> | <!-- verbatim banner string in rendered DOM (see P1-AC1) --> |
| Golden-path smoke | <!-- yes --> | <!-- the § (b) script runs end-to-end asserting the row count + chart --> |
| Production driver | <!-- yes IF a DB is present in P1, else n/a — state which --> | <!-- e.g. tests run on the shipped DuckDB file, not an in-memory substitute --> |
| README current | <!-- yes --> | <!-- every README command in § (b) works verbatim from the stated dir --> |
| Eval threshold | <!-- n/a — no live agent behaviour until Phase 2 --> | <!-- n/a --> |

### (e) Explicitly deferred from Phase 1

<!-- FILL IN: ONE ROW PER capability shaped/stubbed in P1 (or hinted by the brief) that P1
     does NOT make real. Disposition is "→ Phase N" (N must exist in § Phase Overview) — never
     blank, never "TBD". Each MUST be consistent with vision.md Non-Scope. -->

| Item (deferred from P1) | Disposition (→ Phase N) | Stub it leaves behind (api.md / ui.md ref) |
|-------------------------|-------------------------|--------------------------------------------|
| <!-- e.g. real NL→SQL answer --> | <!-- → Phase 2 --> | <!-- POST /query stub (api.md) --> |
| <!-- e.g. dataset delete --> | <!-- → Phase 3 --> | <!-- n/a (not in P1 shell) --> |
| <!-- add a row per deferred capability --> | | |

### (f) Error codes introduced (Phase 1)

<!-- FILL IN: ONE ROW PER named error code this phase introduces (referenced by any Unwanted
     PN-ACn above). Each id MUST match an error.code in api.md's error matrix BYTE-FOR-BYTE —
     this is the single reconciled list so the executor never cross-walks two files by hand.
     A code used in a PN-ACn but absent from api.md's matrix (or vice-versa for codes this phase
     owns) is drift and is REJECTED. If the phase introduces none, write "None — this phase adds
     no new error codes." Do not leave blank. -->

| Error code | Trigger condition | api.md matrix row (endpoint + status) | PN-ACn that asserts it |
|------------|-------------------|----------------------------------------|------------------------|
| <!-- e.g. UNSUPPORTED_FILE --> | <!-- e.g. upload is not a valid CSV --> | <!-- e.g. POST /upload → 422 (api.md) --> | <!-- e.g. P1-AC4 --> |
| <!-- add one row per error code this phase introduces --> | | | |

---

## Later Phases

<!-- FILL IN: ONE ### subsection per subsequent phase (2..N), each with the SAME rigour as
     Phase 1 — the rigour does NOT trail off after Phase 2. These subsections ARE the roadmap;
     there is no separate ROADMAP.md. Below, BOTH Phase 2 and Phase 3 are given as FULL empty
     skeletons (not a "same as above" prose shortcut) precisely so an under-filled later phase
     shows up as visibly empty cells, not as prose-excusable thinness. Copy the full block for
     Phase 4, 5, … — never degrade to "same structure as the prior phase".

     Each subsection MUST contain, in order:
       1. A one-line theme + what becomes real / what is new (verb + object, not a layer).
       2. Scope table: Capability | New or Upgraded-from-stub | Frozen contract + swap note.
          A row that upgrades an earlier stub MUST give TWO things: (a) the api.md/ui.md
          section+anchor it replaces, AND (b) an explicit "shape-frozen / value-changes" line
          stating which fields change vs which bytes stay byte-identical at swap.
       3. Acceptance Criteria (EARS) table: PN-ACn | EARS | Fixture+expected value | test | →SC
          (same five-column bar as Phase 1, including the exact fixture and the runnable assert).
          For eval-backed criteria the test MUST cite the eval case by FILE PATH + case id AND
          the threshold by VALUE (e.g. evals/cases/top5.json#top5 PASS at score ≥ 0.9). "PASS at
          threshold" with no case path and no numeric threshold is INCOMPLETE → gate fails.
       4. "Depends on": the NAMED prior-phase acceptance condition(s) (e.g. "P1 user-accepted;
          POST /query shape frozen at api.md §POST /query → Response 200").
       5. Applicable hard gates: the phase that introduces LIVE agent behaviour MUST include
          Eval threshold; any phase that introduces a DB MUST include Production driver.
       6. "Error codes introduced": same reconciled-with-api.md mini-table as Phase 1 (f).
       7. "Still deferred": what this phase still pushes to a later phase (→ Phase N, never blank). -->

### Phase 2 — <!-- theme, e.g. Ask a question and get a real model-generated answer -->

<!-- One line: what becomes real (names the stub it replaces by anchor), what is new. -->

**Scope:**

| Capability | New or Upgraded-from-stub | Frozen contract + swap note (anchor; which bytes change vs stay identical) |
|------------|---------------------------|----------------------------------------------------------------------------|
| <!-- e.g. NL→SQL answer --> | <!-- Upgraded from P1 stub --> | <!-- replaces api.md §POST /query → Response 200; SHAPE-FROZEN: keys/types byte-identical, only the `rows` VALUES become real --> |
| <!-- e.g. audit logging --> | <!-- New --> | <!-- writes audit_log row per query; columns frozen in data-model.md §audit_log --> |

**Acceptance Criteria (EARS):**

| id | EARS statement (one EARS form, with a quantity) | Fixture + expected value (file, count, literal answer) | Acceptance test (eval case path#id + threshold / pytest node / UI clicks + `assert`) | → SC |
|----|------------------------------------------------|--------------------------------------------------------|----------------------------------------------------------------------------------------|------|
| P2-AC1 | <!-- e.g. WHEN a question is asked in live mode, the system SHALL execute model-generated SQL and return ≥1 row matching the data. --> | <!-- e.g. sample.csv (100 rows); "top 5 products" → rows == [Widget A..E], row_count == 5. --> | <!-- e.g. evals/cases/top5.json#top5 PASS at score ≥ 0.9; `assert score >= 0.9`. --> | <!-- SC-? --> |
| P2-AC2 | <!-- e.g. The system SHALL write exactly one audit_log row per SQL execution, each with duration_ms ≥ 0. --> | <!-- e.g. run 1 query; expected: audit_log count delta == 1, duration_ms >= 0. --> | <!-- e.g. pytest tests/test_audit.py::test_one_row — `assert count_after - count_before == 1 and row.duration_ms >= 0`. --> | <!-- SC-? --> |
| P2-AC3 | <!-- Unwanted: e.g. IF the model returns invalid SQL, THEN the system SHALL return error.code "BAD_SQL" and the UI SHALL keep the prior result visible. --> | <!-- e.g. inject non-SELECT SQL; expected error.code == "BAD_SQL"; prior table DOM unchanged. --> | <!-- e.g. force invalid SQL; `assert r.json()["error"]["code"] == "BAD_SQL"` AND prior table still in DOM. --> | <!-- SC-? --> |

**Depends on:** <!-- e.g. P1 user-accepted; POST /query request/response shape frozen at api.md §POST /query → Response 200 — Phase 2 builds the live agent behind the P1 stub contract. -->

**Applicable hard gates:** <!-- e.g. Offline stub, Live-server, Live-UI, Stub-banner, Golden-path smoke, README current, Production driver (DB now live), AND Eval threshold (FIRST live agent behaviour — MUST appear; harness/rules/testing.md Evals). -->

**Error codes introduced:**

| Error code | Trigger condition | api.md matrix row (endpoint + status) | PN-ACn that asserts it |
|------------|-------------------|----------------------------------------|------------------------|
| <!-- e.g. BAD_SQL --> | <!-- e.g. model returns non-executable / non-SELECT SQL --> | <!-- e.g. POST /query → 422 (api.md) --> | <!-- e.g. P2-AC3 --> |

**Still deferred:** <!-- e.g. saved dashboards → Phase 3; dataset delete → Phase 3. -->

<!-- ============ copy the FULL block above (all 7 parts) for each later phase ============ -->

### Phase 3 — <!-- theme, e.g. Save, list, and delete datasets across sessions -->

<!-- One line: what becomes real (names any stub it replaces by anchor), what is new. -->

**Scope:**

| Capability | New or Upgraded-from-stub | Frozen contract + swap note (anchor; which bytes change vs stay identical) |
|------------|---------------------------|----------------------------------------------------------------------------|
| <!-- e.g. persisted sessions --> | <!-- New / Upgraded from P2 stub --> | <!-- if upgrading: anchor + shape-frozen/value-changes line; if new: n/a --> |
| <!-- add one row per capability --> | | |

**Acceptance Criteria (EARS):**

| id | EARS statement (one EARS form, with a quantity) | Fixture + expected value (file, count, literal answer) | Acceptance test (eval case path#id + threshold / pytest node / UI clicks + `assert`) | → SC |
|----|------------------------------------------------|--------------------------------------------------------|----------------------------------------------------------------------------------------|------|
| P3-AC1 | <!-- EARS, one form, with a quantity --> | <!-- exact fixture + literal expected value --> | <!-- runnable proof with `assert` --> | <!-- SC-? --> |
| P3-AC2 | <!-- EARS --> | <!-- --> | <!-- --> | <!-- SC-? --> |
| <!-- add rows; at least one Unwanted (IF…THEN) criterion naming an error code --> | | | | |

**Depends on:** <!-- e.g. P2 user-accepted + named contract anchor it builds behind --> 

**Applicable hard gates:** <!-- list by name; Production driver if a DB is introduced/changed here; Eval threshold if agent behaviour changes --> 

**Error codes introduced:**

| Error code | Trigger condition | api.md matrix row (endpoint + status) | PN-ACn that asserts it |
|------------|-------------------|----------------------------------------|------------------------|
| <!-- one row per code, or "None — this phase adds no new error codes." --> | | | |

**Still deferred:** <!-- → Phase N, never blank -->

---

## Inter-Phase Dependency Map

<!-- FILL IN: make the build order explicit. TWO mandatory parts:
       1. The ASCII (or mermaid) dependency diagram in the LIVE fenced block below — overwrite
          the example node names, never leave 'TODO'. Every phase number in § Phase Overview
          MUST appear in this diagram, and every node here MUST be a phase that exists above
          (same enumerable cross-check as the table) — a name in one but not the other is
          REJECTED. Do NOT ship the example labels verbatim.
       2. The table: Phase | Cannot start until | Reason.
     RULES:
       - Encode the user-acceptance boundary: a phase CANNOT START until the prior phase is
         USER-ACCEPTED.
       - Name any cross-phase contract dependency by ANCHOR (e.g. "Phase 2 needs Phase 1's
         api.md §POST /query shape frozen"). These are the freeze points the planner relies on.
       - The graph MUST be ACYCLIC. -->

```
P1 ──user-accepted──► P2 ──user-accepted──► P3
      (api.md §POST /query      (live query
       shape frozen)             history exists)
```

| Phase | Cannot start until | Reason (named contract anchor / acceptance condition) |
|-------|--------------------|-------------------------------------------------------|
| 1 | — | first phase; no upstream dependency |
| 2 | <!-- e.g. P1 user-accepted; api.md §POST /query shape frozen --> | <!-- e.g. builds the live agent behind the P1 stub contract --> |
| 3 | <!-- e.g. P2 user-accepted --> | <!-- e.g. persistence assumes live query history exists --> |
| <!-- N --> | <!-- prior phase user-accepted + named contract anchor --> | <!-- --> |

**Acyclicity (REQUIRED — state the literal result):** <!-- write exactly "DAG — acyclic, verified" after confirming no cycle. A cycle, or a missing statement, fails the gate. -->

---

## Explicitly Deferred (Cross-Phase)

<!-- FILL IN: the SINGLE consolidated list of everything intentionally NOT built in any
     currently-planned phase — the "never, by design" items plus anything beyond Phase N.
     This is the bottom of the roadmap; it replaces what a ROADMAP.md would have held.
     RULES:
       - Disposition is EXACTLY one of: "→ Phase N" (N exists above) OR "never — <product-thesis
         reason>". NEVER blank, "TBD", "maybe", or "later".
       - The "Consistent with" cell MUST QUOTE the exact vision.md Non-Scope row text it pairs
         with (not just name it), so the match is checkable from THIS file. Bidirectional law:
         (1) every "→ Phase N" disposition here MUST cite a vision.md Non-Scope row whose own
         disposition is the SAME "→ Phase N", and (2) every "never" here MUST pair a vision.md
         Non-Scope "never" row with a matching reason. A disposition that disagrees with its
         cited vision.md row (e.g. "→ Phase 4" here but "never" in vision.md) is drift → REJECTED.
       - No item deferred here may be promised as in-scope in any phase above.
       - "never" rows state the product-thesis reason (why it is out of the product, by design). -->

| Item | Disposition (→ Phase N / never — reason) | Consistent with (QUOTE the vision.md Non-Scope row + its disposition) |
|------|------------------------------------------|----------------------------------------------------------------------|
| <!-- e.g. Multi-user auth / RBAC --> | <!-- never — single-tenant local demo by design --> | <!-- vision.md Non-Scope: "Multi-user auth — never (single-tenant by design)" --> |
| <!-- e.g. Saved dashboards --> | <!-- → Phase 4 (theme only, not yet scoped) --> | <!-- vision.md Non-Scope: "Saved dashboards — → Phase 4" --> |
| <!-- e.g. Mobile-responsive layout --> | <!-- never for v1 — desktop demo by design --> | <!-- vision.md Non-Scope: "Mobile layout — never for v1 (desktop demo)" --> |
| <!-- add a row per excluded/deferred capability; no blank dispositions; quote the vision row --> | | |

---

## Gaps & Assumptions

<!-- FILL IN: every open planning question. Use [NEEDS CLARIFICATION: ...] ONLY for genuinely
     phase-shaping unknowns (e.g. "does Phase 2 need streaming, which changes the POST /query
     contract?"). Use [ASSUMPTION: value] for anything defaulted (e.g. [ASSUMPTION: Phase 3
     persistence uses the same DuckDB file]). Never leave a blank cell, a silent default, or a
     'TBD' anywhere above — record it here instead. Delete this section only when truly empty. -->

| Item | Type | Resolution / Owner |
|------|------|--------------------|
| <!-- e.g. Phase 4 scope --> | <!-- ASSUMPTION / NEEDS CLARIFICATION --> | <!-- the value chosen, or the question + who answers --> |

---

## Traceability Ledger

<!-- FILL IN: this is the MECHANICAL proof of the TRACEABILITY LAW (top of file). It is NOT a
     prose "coverage looks good" — it is two tables that are filled and self-checked at the
     pre-code gate. An empty or partial ledger BLOCKS the gate. -->

### Matrix A — SC → Phases (every vision.md SC must be advanced by ≥1 phase)

<!-- ONE ROW per SC-N in vision.md — and that means ALL of them: the four labelled rows
     (SC-CORE, SC-UX, SC-STUB, SC-FAIL) AND every free SC-N. Copy the SC ids verbatim from
     vision.md § Success Criteria. The "Advanced by" cell lists the PHASE NUMBER(S) whose
     "Advances SCs" column names this SC. A row whose "Advanced by" cell is empty is an
     UNCOVERED SC → CRITICAL gap, gate fails. The set of SC ids here MUST equal the set in
     vision.md exactly — a missing id or an extra invented id is drift → REJECTED. -->

| SC id (verbatim from vision.md) | Advanced by phase(s) | First PN-ACn that asserts it |
|---------------------------------|----------------------|------------------------------|
| SC-CORE | <!-- e.g. 1, 2 --> | <!-- e.g. P1-AC3 --> |
| SC-UX   | <!-- --> | <!-- --> |
| SC-STUB | <!-- e.g. 1 --> | <!-- e.g. P1-AC1 --> |
| SC-FAIL | <!-- --> | <!-- e.g. P1-AC4 --> |
| <!-- SC-N: add one row per free SC-N in vision.md; none may be omitted --> | | |

**Self-check (state the result):** <!-- "Every SC-N in vision.md appears above with a non-empty 'Advanced by'." — if any is empty, mark it [NEEDS CLARIFICATION: which phase advances SC-N?] and the gate fails. -->

### Matrix B — PN-ACn → SC (every criterion cites a resolving SC)

<!-- ONE ROW per PN-ACn across ALL phases. The "Cites SC" cell MUST be an SC id that appears
     in Matrix A (i.e. exists in vision.md). A PN-ACn whose cited SC does not resolve to a
     Matrix-A row is drift → REJECTED. A PN-ACn with no cited SC is INCOMPLETE → gate fails. -->

| PN-ACn | Phase | Cites SC (must exist in Matrix A) |
|--------|-------|-----------------------------------|
| P1-AC1 | 1 | <!-- SC-? --> |
| P1-AC2 | 1 | <!-- SC-? --> |
| <!-- add one row per PN-ACn in every phase; the set MUST equal the union of all phase AC tables --> | | |

**Self-check (state the result):** <!-- "Every PN-ACn above cites an SC present in Matrix A; every PN-ACn defined in a phase table appears here." — any mismatch fails the gate. -->
