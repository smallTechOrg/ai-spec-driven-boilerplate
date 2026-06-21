# Vision — Product Definition & Contract of Intent

> **Placeholder.** The researcher fills every section thoroughly at intake — highly technical and exact, no vague prose.

<!--
  ROLE OF THIS FILE
  This is the WHAT doc and the contract of intent. It names what is built, for whom,
  the measurable outcomes that define success, the explicit non-scope, and the hard
  constraints. It is the one prose-tolerant doc — but every claim is quantified and
  every success is EARS-tested. No HOW belongs here (no schemas, no endpoints, no
  component topology) — those live in architecture.md / data-model.md / api.md /
  ui.md / agent-graph.md.

  ONE FACT, ONE PLACE — this file is the single home for the product Success Criteria
  (SC-N), the Non-Scope fence, and the Hard Constraints. Other docs reference these by
  id/link; they never redefine them. Conversely, this file does NOT redefine facts that
  live elsewhere — it links to them:
    - per-phase plan & criteria (PN-ACn) ......... spec/delivery-plan.md
    - stack choices + version pins ............... spec/architecture.md
    - /health shape + stub_mode flag ............. spec/api.md
    - audit_log columns .......................... spec/data-model.md
    - port numbers ............................... defined once in Hard Constraints below

  TRACEABILITY LAW (bidirectional, enforced at the pre-code spec gate):
    - every SC-N below MUST be advanced by ≥1 phase in delivery-plan.md
    - every per-phase criterion (PN-ACn) in delivery-plan.md MUST cite the SC-N it serves
    - every SC-N below MUST ALSO cite the api.md endpoint (§<METHOD /path>) OR the
      data-model.md entity that proves it (SC ↔ contract) — not only a phase. This closes
      the gap where vision is fully filled but the technical contracts an executor needs
      are still stubs.
    - an SC with no phase, an SC with no contract cite, or a phase criterion with no SC,
      is INCOMPLETE → gate fails
-->

---

## Product Definition

<!-- FILL IN: ONE precise paragraph. It MUST name, explicitly:
       (1) the concrete INPUT type(s) WITH format — e.g. "CSV/Parquet file upload",
           "natural-language query string", "PDF document (≤ 20 MB)". Name the format,
           not just "data".
       (2) the TRANSFORMATION — the noun for the system (agentic data analyst,
           document-extraction pipeline, retrieval chat service, …) and what it does to
           the input.
       (3) the concrete OUTPUT type(s) WITH rendering medium — e.g. "Markdown table
           rendered to a sortable HTML grid", "interactive Plotly chart", "JSON object
           with named fields", "downloadable .xlsx".
       (4) the single PRIMARY ACTOR (one human role — the one this product is FOR).
     FORBIDDEN words: 'leverages', 'seamless', 'powerful', 'AI-powered' (unless a model
     is named), 'robust', 'cutting-edge', 'best-in-class'. If the product uses an LLM and
     no model provider is named, write [NEEDS CLARIFICATION: which model/provider?].
     Length: 3–5 sentences. No bullet list — this is the one paragraph that earns prose. -->

<!-- e.g. (DELETE — this is an illustration, not your answer):
     A browser application for a single operations analyst. The analyst uploads one or
     more CSV files (UTF-8, ≤ 200 MB each) and asks an ad-hoc question as an English
     string. The system is an agentic data analyst: it translates the question to SQL,
     executes it against the uploaded data in a local DuckDB file, and returns the result
     as a Markdown table rendered to a sortable HTML grid plus an interactive Plotly chart.
     Every generated SQL query is written to an audit log. -->

**In one sentence:**
<!-- FILL IN: ONE sentence an engineer could repeat verbatim to describe the product.
     Must contain input + transformation + output + actor. No subordinate clauses that
     hide scope. This sentence is quoted in delivery-plan.md Phase 1's goal. -->
> _<single-sentence product statement>_

### Input contract

<!-- FILL IN: the field-level shape of the PRIMARY input artefact. Use the SAME typed
     tokens as api.md (string | int | float | bool | ISO-8601 | array<T> | object{…} | null).
     A row whose Type is prose ("data", "a file", "text") instead of a typed token is REJECTED.
     EITHER fill this mini-table OR replace it with EXACTLY the line:
        "Full input shape: spec/api.md §<METHOD /path>"
     and nothing else — and that anchor MUST resolve to a non-placeholder endpoint in api.md.
     The gate REJECTS the section if neither a fully-typed mini-table nor a resolving
     api.md link is present. -->

| Field | Type (api.md token) | Constraint |
|-------|---------------------|------------|
| <!-- e.g. file --> | <!-- e.g. object{name: string, bytes: int} --> | <!-- e.g. content-type text/csv, ≤ 200 MB --> |
| <!-- e.g. question --> | <!-- e.g. string --> | <!-- e.g. 1..2000 chars, non-empty --> |

### Output contract

<!-- FILL IN: the field-level shape of the PRIMARY output artefact, same rules as above.
     EITHER this typed mini-table OR exactly "Full output shape: spec/api.md §<METHOD /path>". -->

| Field | Type (api.md token) | Constraint |
|-------|---------------------|------------|
| <!-- e.g. rows --> | <!-- e.g. array<object{…}> --> | <!-- e.g. length ≥ 1 on a matching query --> |
| <!-- e.g. chart_spec --> | <!-- e.g. object{…} | null --> | <!-- e.g. null when result is non-numeric --> |

---

## Users & Jobs

<!-- FILL IN: ONE ROW PER DISTINCT USER. At least one row. Most demos have exactly one
     primary actor — do not invent personas to pad the table.
       - User ............ short label (e.g. "Analyst", "Reviewer")
       - Role ............ concrete context, NOT an adjective (e.g. "Ops, cannot write SQL",
                           "Compliance officer, read-only"). "Power user" is REJECTED.
       - Primary job ..... the concrete task they arrive to do, VERB-FIRST
                           (e.g. "Answer an ad-hoc data question from an uploaded CSV").
                           A persona ("wants insights") is REJECTED — name the task.
       - Success signal .. the single MEASURABLE signal that the product worked for them,
                           WITH a quantity, AND a "(→ SC-N)" pointer to the Success Criteria
                           row it maps to. Every success signal MUST trace to an SC below. -->

| User | Role (concrete, not an adjective) | Primary job (verb-first task) | Success signal (measurable → SC) |
|------|-----------------------------------|-------------------------------|----------------------------------|
| <!-- e.g. Analyst --> | <!-- e.g. Ops, non-SQL --> | <!-- e.g. Answer an ad-hoc question from a CSV --> | <!-- e.g. Correct answer table + chart in < 5 s without writing SQL (SC-2, SC-4) --> |
| <!-- add rows only for genuinely distinct users --> | | | |

<!-- HARD BAR: every "Success signal" cell (1) names a QUANTITY, (2) ends with a (→ SC-N)
     reference, and (3) that SC-N exists in the Success Criteria table below. STRONGER:
     the quantity in the Success-signal cell MUST appear VERBATIM in the referenced SC-N
     row — a "< 5 s" signal MUST point at an SC whose EARS statement contains "5 s".
     The gate REJECTS the row if the number/threshold does not match the cited SC.
     No quantity, no SC pointer, or a mismatched number → gate fails. -->

---

## Problem & Current Baseline

<!-- FILL IN: the EXACT manual or broken process this product replaces. Two parts, both
     mandatory:
       (a) BEFORE — name the existing tool, the friction, and the CURRENT COST expressed
           as a QUANTITY: minutes per task, % error rate, $/month, headcount. If a number
           is genuinely unknown, write it as [ASSUMPTION: <assumed value> — <source>],
           NEVER a blank. A problem statement with no quantified baseline is REJECTED at
           the pre-code spec gate as incomplete.
       (b) AFTER — the corresponding target as a quantity, on the SAME axis as the before
           (if before is "15 min/question", after is "< 30 s/question").
     Keep it to one short paragraph + the table. The table is the load-bearing part.

     SOURCE DISCIPLINE (bounds the [ASSUMPTION] escape): the "Source of before number"
     cell MUST be exactly one of: {measured, vendor-doc, prior-build-log, user-stated},
     optionally with a short note. Bare "gut feel", "estimate", "roughly", or a blank is
     REJECTED. An [ASSUMPTION] with no verifiable source class is treated as
     [NEEDS CLARIFICATION] and BLOCKS the pre-code gate until the user confirms it. -->

<!-- e.g. (DELETE): Today the analyst pastes the CSV into a spreadsheet and builds pivot
     tables by hand. Each question takes ~15 min and ~1 in 5 results contains a formula
     error [ASSUMPTION: 20% error — from team retro]. This product replaces the manual
     spreadsheet step with a SQL-verified query path. -->

| Axis | Before (current, quantified) | After (target, quantified) | Source class (measured \| vendor-doc \| prior-build-log \| user-stated) |
|------|------------------------------|----------------------------|------------------------------------------------------------------------|
| Time per task | <!-- e.g. ~15 min/question (manual pivot) --> | <!-- e.g. < 30 s/question --> | <!-- e.g. measured (team retro) --> |
| Error rate | <!-- e.g. ~20% formula error --> | <!-- e.g. 0% (SQL-verified, deterministic) --> | <!-- e.g. user-stated --> |
| <!-- $ cost / headcount / other --> | <!-- --> | <!-- --> | <!-- one of the four source classes — NOT "gut feel"/"estimate"/blank --> |

---

## Success Criteria (EARS)

<!-- FILL IN: the PRODUCT-LEVEL, cross-cutting outcomes that define "this is the right
     product". These are product-wide and outlive any single phase. Per-phase criteria
     (PN-ACn) live in delivery-plan.md and each trace UP to an SC here.

     EACH ROW:
       - # ............. SC-N (stable id; never renumber once referenced)
       - EARS statement  EXACTLY ONE of these five forms, with a QUANTITY:
            Ubiquitous : "The <system> SHALL <observable outcome with quantity>."
            Event      : "WHEN <trigger>, the <system> SHALL <outcome with quantity>."
            State      : "WHILE <state>, the <system> SHALL <outcome with quantity>."
            Unwanted   : "IF <condition>, THEN the <system> SHALL <recovery with quantity>."
            Optional   : "WHERE <feature present>, the <system> SHALL <outcome with quantity>."
       - Acceptance test  the EXACT proof. It MUST name BOTH:
            (a) the artefact LOCATION — a `pytest` node id (path::test_name), a full curl
                command, or a DOM selector / click sequence; AND
            (b) the asserted LITERAL as a PARSEABLE assertion, written in one of these forms:
                  assert <lhs> == <value>      (exact-value assertion)
                  assert <count> >= <n>        (minimum-quantity assertion)
            Prose like "it works", "returns 200", or a named-but-empty test
            ("pytest …::test_query — runs the query") is REJECTED — the assertion must
            pin a specific field/value/count, not merely run code.

     HARD BAR (stub-immunity): NO criterion may be satisfied by a stub that returns an
     empty list and a 200. Each MUST name a USER-VISIBLE ARTEFACT with a quantity or a
     named field — a row_count ≥ 1, a chart with axis labels + tooltips, an audit row with
     a duration_ms, a named JSON field with a typed value.

     COVERAGE — FOUR LABELLED ROWS ARE NON-DELETABLE. The four pre-labelled rows below
     (SC-CORE, SC-UX, SC-STUB, SC-FAIL) MUST each be filled; a blank labelled row is a
     visibly-empty REQUIRED cell, not a silent omission. Each has a mandatory EARS form:
       - SC-CORE  the core happy-path outcome (the thing the product is FOR).
       - SC-UX    the UX floor (interactive artefact: sortable table w/ row count OR Plotly
                  chart w/ axis labels + tooltips + PNG download — a bare HTML table /
                  static PNG FAILS).
       - SC-STUB  the offline-stub contract (runs with no key, no network — api.md stub_mode).
       - SC-FAIL  at least one Unwanted-behaviour criterion — MUST use the IF…THEN form.
     Add free SC-N rows for everything else. The gate asserts all four labelled rows are
     non-empty AND that SC-FAIL uses the IF…THEN EARS form.

     TRACEABILITY (SC ↔ phase ↔ contract): every SC below MUST (1) be advanced by ≥1 phase
     in delivery-plan.md, AND (2) cite in its EARS or test cell the api.md endpoint
     (§<METHOD /path>) OR data-model.md entity that proves it. An SC that traces only to a
     phase but to no technical contract is INCOMPLETE → gate fails. -->

| # | EARS statement (one EARS form, with a quantity + a contract cite) | Acceptance test (location + parseable assertion) |
|---|-------------------------------------------------------------------|---------------------------------------------------|
| SC-CORE | <!-- REQUIRED, core happy-path. e.g. WHEN a query matches ≥1 row, the API SHALL return rows with length ≥ 1 (api.md §POST /query). --> | <!-- e.g. `pytest tests/test_query.py::test_top5` — assert resp.json()["row_count"] == 5 --> |
| SC-UX | <!-- REQUIRED, UX floor. e.g. WHEN a query returns numeric data, the UI SHALL render a Plotly chart with axis labels, hover tooltips, and a PNG download button (api.md §POST /query → chart_spec). --> | <!-- e.g. Ask "revenue by month"; assert document.querySelectorAll(".modebar").length >= 1 --> |
| SC-STUB | <!-- REQUIRED, offline stub. e.g. IF APP_LLM_PROVIDER=stub THEN the system SHALL pass the full unit suite with no key and no network (api.md stub_mode). --> | <!-- e.g. `APP_LLM_PROVIDER=stub uv run pytest` — assert exit_code == 0 and outbound_calls == 0 --> |
| SC-FAIL | <!-- REQUIRED, IF…THEN form. e.g. IF a query produces invalid SQL, THEN the API SHALL return 422 with error.code == "BAD_SQL" and write 0 audit rows (api.md §POST /query errors; data-model.md audit_log). --> | <!-- e.g. `pytest tests/test_query.py::test_bad_sql` — assert resp.status_code == 422 and resp.json()["error"]["code"] == "BAD_SQL" --> |
| SC-5 | <!-- add free SC-N rows for the rest; same EARS + contract-cite + parseable-assertion bars --> | <!-- --> |

> **Weak vs Strong — EARS statement (do not ship Weak):**
> - **Weak** (REJECTED — stub-passable): "The system SHALL return a list of results." — an empty `[]` + 200 satisfies it.
> - **Strong** (accepted): "WHEN a query matches ≥1 row, the API SHALL return a JSON array whose first element has a non-null `value: float` field (api.md §POST /query), and the UI SHALL render it in a sortable table showing the row count." — names a typed field, a quantity, a user-visible artefact, AND a contract anchor.
>
> **Weak vs Strong — Acceptance test (do not ship Weak):**
> - **Weak** (REJECTED — empty assertion): "`pytest tests/test_query.py::test_query` — runs the query." — names a node but asserts nothing real.
> - **Strong** (accepted): "`pytest tests/test_query.py::test_query` — assert len(resp.json()["rows"]) >= 1 and resp.json()["rows"][0]["value"] is not None." — names the node AND a parseable assertion over a specific field.

---

## Non-Scope

<!-- FILL IN: what the product explicitly does NOT do, across ALL currently-planned
     phases. This is the anti-scope-creep fence. EACH excluded capability gets a
     DISPOSITION that is one of exactly two shapes:
        "→ Phase N"  — deferred; Phase N MUST exist in delivery-plan.md.
        "never — <one-line reason>" — out of the product thesis or by design.
     'Disposition' may NOT be blank, "TBD", "maybe", or "later". There is NO separate
     ROADMAP file — every deferral target is a phase number in delivery-plan.md.

     Include the obvious creep vectors so the fence is explicit: auth/RBAC, multi-tenant,
     saved/persisted state, real-time collaboration, mobile, i18n, data export beyond the
     stated output, and any "phase 2" feature the brief hints at. -->

| Excluded capability | Disposition (→ Phase N in delivery-plan.md / never — reason) |
|---------------------|-------------------------------------------------------------|
| <!-- e.g. Multi-user auth / RBAC --> | <!-- e.g. never — single-tenant local demo by design --> |
| <!-- e.g. Saved dashboards --> | <!-- e.g. → Phase 3 --> |
| <!-- e.g. Real-time collaborative editing --> | <!-- e.g. never — out of product thesis --> |
| <!-- add a row for every creep vector the brief implies but the product won't do --> | |

---

## Hard Constraints

<!-- FILL IN: the non-negotiable limits that bind EVERY phase. The rows marked REQUIRED
     below MUST be present and filled with a REAL, CONFIRMED value. Each API-key row names
     the ENV VAR NAME, never a secret value. Port numbers and the /health shape have their
     single home as noted — reference, don't duplicate.

     NO-DEFAULT-BY-UNCOMMENTING RULE: each Value cell ships as a "<!-- FILL IN: … (harness
     default X — confirm or override) -->" prompt, NOT a pre-seeded answer. The gate FLAGS
     any Value that is byte-identical to its template comment, or still wrapped in the
     comment fence — a default must be CONFIRMED by the researcher writing it as a real
     value, not inherited by leaving the comment in place.

     REQUIRED rows (must all appear, each with a confirmed value):
       - Phase-1 build ceiling .... harness default 30 min (hard) — confirm or override
       - Backend port ............. harness default :8001
       - Frontend port ............ harness default :3000
       - Deploy target ............ harness default local demo (Render ONLY on explicit request)
       - Database ................. DuckDB or SQLite, LOCAL FILE — NO server DB
       - LLM provider switch ...... the env var that selects live-vs-stub (see api.md stub_mode)
       - Every required API key ... one row each, as an ENV VAR NAME + when it's required
       - Runtime budget ........... p95 latency, per-query timeout, max rendered rows
       - Concurrency / volume ..... max concurrent sessions, max result rows × columns

     Replace the `APP_` prefix with the project's real env prefix consistently. -->

| Constraint | Value (confirm or override — NOT the template comment) |
|------------|--------------------------------------------------------|
| Phase-1 build ceiling | <!-- FILL IN: build ceiling (harness default 30 min hard — confirm or override). Phase 1 is a shaped first release; UI present even if data paths stubbed, stub-mode banner visible --> |
| Backend port | <!-- FILL IN: backend port (harness default :8001 — confirm or override) --> |
| Frontend port | <!-- FILL IN: frontend port (harness default :3000 — confirm or override) --> |
| Deploy target | <!-- FILL IN: deploy target (harness default local demo; Render only on explicit request) --> |
| Database engine | <!-- FILL IN: DuckDB or SQLite, local file e.g. `./data/app.db` — NO server DB --> |
| LLM provider switch | <!-- FILL IN: e.g. `APP_LLM_PROVIDER` ∈ {stub, google, …}; `stub` ⇒ no key, no network (api.md stub_mode) --> |
| LLM API key | <!-- FILL IN: e.g. `APP_GEMINI_API_KEY` — REQUIRED when `APP_LLM_PROVIDER=google`; env var NAME only, never the value --> |
| <!-- other required key, one row each --> | <!-- FILL IN: e.g. `APP_<SERVICE>_API_KEY` — required when … --> |
| Max upload / input size | <!-- FILL IN: e.g. 200 MB/file — name the limit if the product takes uploads --> |
| Single-tenant | <!-- FILL IN: e.g. yes — no auth, one local user (matches Non-Scope) --> |
| **Runtime budget** (REQUIRED) | <!-- FILL IN: authoritative runtime limits — p95 query latency (e.g. ≤ 5 s), per-query hard timeout (e.g. 30 s), max rendered rows (e.g. 10 000). These bind every phase and are cited by SC-CORE / SC-UX. A build-time ceiling alone is NOT enough. --> |
| **Concurrency / volume envelope** (REQUIRED) | <!-- FILL IN: max concurrent sessions (e.g. 1 — single-tenant local), max result rows × columns (e.g. 100 000 rows × 64 cols), max upload count per session. data-model.md sizing + api.md pagination derive from this. --> |

<!-- NOTE: the live `/health` response shape and the `stub_mode` flag are defined ONCE in
     spec/api.md — reference them here, do not restate the JSON. -->
