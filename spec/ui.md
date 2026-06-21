# UI — Interface Contract

> **Placeholder.** The researcher fills every section thoroughly at intake — highly technical and exact, no vague prose.

<!-- OPTIONAL DOC: Delete this file ONLY if the product genuinely has no UI (pure CLI, pure
     library, or headless service). A "we'll add a UI later" project is NOT no-UI — if any phase
     in delivery-plan.md ships a screen, this file is mandatory and Phase 1 MUST include the
     visible shell (even with every data path stubbed) plus the stub-mode banner.

     This is the INTERFACE CONTRACT, not a mood board. It states observable structure: the
     stack pins, the screen inventory, the four states per screen, and the component UX bar the
     executor must clear. Behaviour ("the user feels X") lives in vision.md; per-phase pass/fail
     EARS criteria live in delivery-plan.md. This file says WHAT the interface IS — never HOW a
     component is coded (that is src/). -->

This document is the exact, testable interface contract. Every screen is designed for all four
states. Every component meets the UX bar. The executor cannot ship a bare-table proof-of-concept
against this spec.

<!-- ONE FACT, ONE PLACE — referenced here, owned elsewhere:
  - the /health response shape + the `stub_mode` flag  → api.md (GET /health)
  - the frontend port + backend port                   → architecture.md (Stack / ports table)
  - the state framework + library versions             → architecture.md (Stack table)
  - the audit_log columns (e.g. duration_ms)           → data-model.md
  - product Success Criteria (SC-N)                     → vision.md
  - per-phase acceptance criteria (PN-ACn, EARS)       → delivery-plan.md
  Cite by id/link. Do NOT restate a shape, a port, or a version here. -->

---

## UI Stack & Global Shell

<!-- FILL IN: Pin the frontend stack and define the global layout. Two parts, both as tables.
     The state-framework + every version pin MUST match architecture.md exactly (do not invent a
     second source of truth — if it differs from architecture.md, the pre-code gate rejects it). -->

### Frontend stack (pins)

<!-- FILL IN: Every row carries a CONCRETE version pin or a version floor + reason ("latest" alone
     is rejected). The table/chart renderer rows are mandatory and carry the named libraries. -->

| Concern | Library | Version pin | Why this choice (1 line) |
|---------|---------|-------------|--------------------------|
| Framework | <!-- e.g. Next.js (App Router) --> | <!-- e.g. 15.x --> | <!-- must match architecture.md --> |
| UI runtime | <!-- e.g. React --> | <!-- e.g. 19.x --> | <!-- --> |
| Styling | <!-- Tailwind CSS --> | <!-- e.g. 3.4.x --> | utility-first; no bespoke CSS files |
| Markdown table renderer | react-markdown + remark-gfm | <!-- e.g. 9.x / 4.x --> | renders GFM tables; **not** `<pre>` dumps |
| Chart renderer | react-plotly.js (+ plotly.js) | <!-- e.g. 2.x / 2.x --> | interactive charts; loaded SSR-safe (see below) |
| Data fetching | <!-- e.g. native fetch / SWR --> | <!-- pin --> | <!-- --> |
| Test runner (UI) | <!-- e.g. Playwright / Vitest --> | <!-- pin --> | drives Live-UI gate (rendered-DOM assert) |

> **SSR guard (mandatory).** `react-plotly.js` touches `window` on import and crashes during
> server render. It MUST be loaded client-only:
> ```tsx
> const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });
> ```
> Any browser-only API (`window`, `localStorage`, `sessionStorage`) is read in `useEffect`,
> never at module/initialiser scope. Cross-ref `harness/patterns/nextjs.md` and gotcha
> **[C-SSR-BROWSER-API]** (`harness/rules/gotchas.md`). `npm run build` passing is necessary,
> not sufficient — the Live-UI gate curls the running `npm run start` origin to exercise the
> request path where this crash surfaces.

### Global shell regions

<!-- FILL IN: Describe the always-present layout as a table. The stub banner and the error-toast
     region are GLOBAL shell elements (present on every screen), not per-screen widgets. Name the
     ports/origins by reference to architecture.md, do not hardcode them in two places. -->

| Region | Position | Always present? | Holds | First phase |
|--------|----------|-----------------|-------|-------------|
| Stub-mode banner | full-width, top | yes (WHILE stub) | the verbatim stub string (see § Stub-Mode Banner) | Phase 1 |
| Top nav / brand | top bar | yes | app name, active-screen marker | Phase 1 |
| Session sidebar | left | <!-- yes/per-phase --> | session list (id/name), active highlighted | <!-- Phase N --> |
| Main region | center | yes | the active screen (query/response, detail, etc.) | Phase 1 |
| Error-toast region | <!-- e.g. top-right --> | yes | transient plain-English errors + recovery action | Phase 1 |

```
<!-- FILL IN: concrete ASCII of the shell. Replace the example. NOT 'TODO'.

     ASCII GATE (checked): the diagram MUST visibly label, by name, EVERY region marked
     "Always present? yes" in the table above, PLUS the stub-banner row and the active-screen
     marker (e.g. the `*` / `>` on the active item). A box that omits any mandatory region — or
     omits the stub-banner row, or shows no active-screen marker — is REJECTED. Example:

 +--------------------------------------------------------------+
 |  STUB MODE — responses are canned, not real AI output        |  <- stub-mode banner (WHILE stub)
 +-----------+--------------------------------------------------+
 |  Sessions |  [ app brand ]  (active: Query)    [error toast] |  <- top nav (active-screen marker)
 |  > S-3 *  |                                                  |  <- session sidebar (* = active)
 |    S-2    |   < main region: active screen >                 |  <- main region
 |    S-1    |                                                  |
 |  + New    |                                                  |
 +-----------+--------------------------------------------------+
-->
```

---

## Screens

### Screen inventory (required floor)

<!-- FILL IN: List EVERY screen/view reachable in the product as a table BEFORE writing the
     per-screen subsections. This is the inventory the gate counts against.

     HARD FLOOR (gate-checked): the inventory MUST cover every UI-bearing phase in
     delivery-plan.md — for each phase that ships a screen there is ≥1 row here tagged with that
     phase. A single-screen fill for a product whose delivery-plan has UI-bearing Phase 2+ is
     REJECTED. Phase 1 MUST include the shell screen (even fully stubbed). The number of rows here
     MUST equal the number of `### <screen>` subsections below (every listed screen is specified). -->

| Screen | First phase (shell / live) | Reachable from | Specified below? |
|--------|----------------------------|----------------|------------------|
| <!-- e.g. Query Result --> | <!-- Phase 1 shell, Phase 2 live --> | <!-- top nav / sidebar / link from X --> | <!-- ✅ §Query Result --> |
| <!-- e.g. Session History --> | <!-- Phase N --> | <!-- sidebar --> | <!-- --> |

<!-- FILL IN: One ### subsection per screen/view LISTED ABOVE. Each subsection MUST have:
       (a) a header tagged `(→ Phase N)` — and where a screen's SHELL appears before its data is
           live, tag both, e.g. `(→ Phase 1 shell, Phase 2 live)`;
       (b) Purpose — one line, the user job done here;
       (c) Key elements — a table enumerating EVERY interactive element (see rule below);
       (d) Actions — a table enumerating EVERY user action (see rule below);
       (e) a MANDATORY four-state table (Loading | Empty | Populated | Error).

     ENUMERATION RULE (gate-checked): Key elements and Actions MUST enumerate EVERY interactive
     element and EVERY user action on the screen — not one example row. A screen listing only the
     example row(s) shipped in this template is REJECTED. Every Action row MUST cite a concrete
     api.md endpoint id OR an explicit follow-up target (another screen / a Component UX Bar
     criterion #). An Action with no backing id is REJECTED.

     A screen missing ANY of the four states is REJECTED at the pre-code gate.

     FOUR-STATE TEETH (gate-checked): each state cell MUST name a CONCRETE artefact — prose like
     "table renders", "shows results", or "no results message" is REJECTED:
       Loading  = the EXACT skeleton geometry (e.g. "render exactly {page-size} pulse rows shaped
                  like the result table + a chart-area placeholder") — never blank, never a layout
                  shift, never just "skeleton".
       Empty    = the LITERAL CTA string the user reads (in `backticks`) — never a silent [] or a
                  bare "no results".
       Populated= a NAMED field AND a quantity it must show (row count / axis label / item count) —
                  the styled content meeting the Component UX Bar below.
       Error    = the LITERAL user-facing message string (in `backticks`) + a NAMED recovery
                  action — never a stack trace, never just "shows an error".
     Cross-ref harness/patterns/ux.md.

     Phase 1 MUST list at least the shell screen with all four states (even fully stubbed). -->

> **Weak vs Strong four-state cells (read before filling):**
> - WEAK: `Populated = table renders` / `Empty = no results message` / `Error = shows an error`.
>   → satisfiable by any DOM; names no field, no string, no quantity. REJECTED.
> - STRONG: `Populated = sortable table with `\`{N} rows\`` in header (N≥1) + Plotly chart with
>   x/y axis titles` / `Empty = headline `\`Ask a question about your data\`` + ≥1 example chip` /
>   `Error = inline `\`Could not run that query\`` + `\`Try again\`` button; prior result stays
>   visible`. Each names the literal string / field / quantity a test can assert.

<!-- EXAMPLE SUBSECTION (for a data-query UI) — DELETE and replace with the real screens listed
     in the inventory above. The rows below are illustrative; shipping them verbatim is REJECTED. -->

### `<!-- Screen name, e.g. Query Result -->` (→ Phase <!-- N, e.g. "1 shell, 2 live" -->)

**Purpose:** <!-- one line: the user job done on this screen -->

**Key elements** (enumerate EVERY interactive element — one row is not an inventory):

| Element | Type | Source / binds to |
|---------|------|-------------------|
| <!-- e.g. query input --> | `<textarea>` + submit button | <!-- POST /api/query (api.md) --> |
| <!-- e.g. result table --> | react-markdown GFM table | <!-- response.table_markdown --> |
| <!-- e.g. result chart --> | react-plotly.js Plot | <!-- response.chart spec --> |
| <!-- e.g. follow-up chips --> | clickable chips | <!-- response.suggestions[] --> |

**Actions** (enumerate EVERY action — each MUST cite an api.md endpoint id OR an explicit follow-up target):

| Action | Trigger | Effect | Backed by (api.md id / screen / UX-bar #) |
|--------|---------|--------|-------------------------------------------|
| <!-- Submit query --> | <!-- click / ⏎ --> | <!-- disables btn, shows progress, renders result --> | <!-- POST /api/query (api.md) --> |
| <!-- Click follow-up --> | <!-- chip click --> | <!-- fills input + auto-submits --> | <!-- UX-bar #10 --> |

**Four states (mandatory):**

| State | What the user sees (concrete) |
|-------|-------------------------------|
| Loading | <!-- e.g. `animate-pulse` skeleton rows shaped like the result table; input stays readable; submit disabled with spinner --> |
| Empty | <!-- e.g. 'Ask a question about your data' headline + ≥1 clickable example chip — never a blank table --> |
| Populated | <!-- e.g. sortable table with **row count in header** + Plotly chart with axis labels + follow-up chips — name a quantity/field --> |
| Error | <!-- e.g. inline red 'Could not run that query' + 'Try again' button; the PRIOR result stays visible — never a stack trace --> |

<!-- REPEAT the ### subsection above for every screen. Examples of likely screens:
       - Query Result (the core ask/answer surface)
       - Dataset / Source list (what data is available)
       - Session / History view (past queries + responses)
       - Detail / drill-down (a single record or chart expanded)
     Each gets a Phase tag and its own four-state table. -->

---

## Component UX Bar

<!-- FILL IN: The non-negotiable component standards that make this a PRODUCT, not a demo. State
     each as ONE EARS criterion paired with an exact acceptance test (a UI click sequence + the
     asserted on-screen string, OR a UI test node id), and cite the PN-ACn in delivery-plan.md it
     maps to and the SC-N in vision.md that phase serves. Source: harness/patterns/ux.md.

     HARD FLOOR (gate-checked):
       1. There MUST be ≥1 criterion per DATA-BEARING screen in the inventory above (a screen that
          renders content the user reads/acts on). A data-bearing screen with no UX-bar row is
          REJECTED.
       2. EVERY criterion names a user-visible artefact with a QUANTITY or a NAMED field (a row
          count ≥1, axis labels present, a chip that fills+submits, an active item highlighted). A
          criterion satisfiable by an empty list + 200 (e.g. "SHALL display results in a table")
          is REJECTED.
       3. EVERY row's `Acceptance test`, `Phase AC`, and `Serves SC` cells MUST be non-empty. A
          row with a blank acceptance test, a blank Phase AC, or a blank Serves SC is REJECTED at
          the pre-code gate. The acceptance test MUST be a runnable reference (UI test node id OR a
          click sequence) ending in an asserted on-screen string/quantity — a cell left as an
          `<!-- ... -->` comment is REJECTED.
       4. TRACE RESOLUTION: each `Phase AC` MUST cite a PN-ACn that EXISTS in delivery-plan.md and
          each `Serves SC` an SC-N that EXISTS in vision.md (bidirectional trace). A citation that
          does not resolve is drift and is REJECTED. -->

> **Weak vs Strong (read before filling):**
> - WEAK: "The app SHALL display query results in a table." → a bare `<table>` with no sort and
>   no row count, or an empty `[]` rendering nothing, passes. REJECTED.
> - STRONG: "WHEN a query returns N≥1 rows the result table SHALL show '`{N} rows`' in its header
>   and clicking a column header SHALL re-sort the rows; assert by clicking 'amount' and reading
>   the first cell flips (P2-AC4 → SC-2)." Cannot pass on a stub-empty-200.

<!-- ========================================================================================
     EXAMPLE BLOCK — criteria 1–13 below are for a DATA-QUERY UI (table / chart / chips /
     sessions). They are a worked example of the BAR, not your product's criteria.

       DELETE this whole example block and replace it with criteria for THIS product's screens,
       one group per data-bearing screen, each row obeying the HARD FLOOR above. Keep the column
       shape and the Weak/Strong box. Shipping criteria 1–13 verbatim for a different product is
       REJECTED (they describe the wrong UI); gutting them with no replacement floor is REJECTED.
       (Criterion 14 — the Stub-Mode Banner — is NOT part of this example; it is mandatory for
       every product and lives in its own section below.)
     ======================================================================================== -->

### Data tables

| # | EARS criterion | Acceptance test (click sequence + asserted string) | Phase AC | Serves SC |
|---|----------------|----------------------------------------------------|----------|-----------|
| 1 | WHEN a result has N≥1 rows the table header SHALL display the exact text `{N} rows`. | <!-- click submit on a seeded query → assert header text matches /\d+ rows/ and N≥1 --> | <!-- P?-AC? --> | <!-- SC-? --> |
| 2 | WHEN a column header is clicked the table SHALL re-sort rows by that column (asc→desc toggle). | <!-- click header twice → assert first row cell value changes --> | <!-- P?-AC? --> | <!-- SC-? --> |
| 3 | IF a result exceeds 50 rows THEN the table SHALL paginate or virtualise (never render all rows into the DOM). | <!-- seed 200 rows → assert rendered `<tr>` count ≤ page size --> | <!-- P?-AC? --> | <!-- SC-? --> |
| 4 | The table SHALL right-align numeric columns and render null cells as `—` (em dash), not blank. | <!-- assert a null cell text === '—' --> | <!-- P?-AC? --> | <!-- SC-? --> |

### Charts

| # | EARS criterion | Acceptance test | Phase AC | Serves SC |
|---|----------------|-----------------|----------|-----------|
| 5 | WHEN a result is charted the chart SHALL render a title, both axis labels, and hover tooltips, and SHALL expose a PNG-download control. | <!-- assert axis-title nodes non-empty + modebar 'Download plot as png' present --> | <!-- P?-AC? --> | <!-- SC-? --> |
| 6 | The chart type SHALL be chosen by data shape: line for time-series, bar for categorical, scatter for two numeric columns. | <!-- seed a time column → assert trace.type === 'scatter'/'line' mode --> | <!-- P?-AC? --> | <!-- SC-? --> |
| 7 | IF a result has no chartable columns THEN the chart area SHALL show 'No data to chart' (never an empty Plotly canvas). | <!-- seed unchartable result → assert text 'No data to chart' visible --> | <!-- P?-AC? --> | <!-- SC-? --> |

### Query / response flow

| # | EARS criterion | Acceptance test | Phase AC | Serves SC |
|---|----------------|-----------------|----------|-----------|
| 8 | WHILE a query is in flight the submit button SHALL be disabled and a progress indicator SHALL show; the input text SHALL NOT clear. | <!-- click submit → assert button[disabled] + spinner visible + input value unchanged --> | <!-- P?-AC? --> | <!-- SC-? --> |
| 9 | WHEN a query errors the error SHALL appear inline and the PRIOR result SHALL remain visible (the error never replaces the last good result). | <!-- force a 500 → assert error text shown AND previous table still in DOM --> | <!-- P?-AC? --> | <!-- SC-? --> |

### Follow-up chips

| # | EARS criterion | Acceptance test | Phase AC | Serves SC |
|---|----------------|-----------------|----------|-----------|
| 10 | WHEN a follow-up chip is clicked the input SHALL be filled with the chip text AND the query SHALL auto-submit. | <!-- click chip → assert input value === chip text AND a new result renders --> | <!-- P2-AC5 --> | <!-- SC-? --> |

### Session sidebar / history

| # | EARS criterion | Acceptance test | Phase AC | Serves SC |
|---|----------------|-----------------|----------|-----------|
| 11 | The sidebar SHALL show each session's visible id/name and SHALL highlight the active session. | <!-- assert active session element has the active class/style --> | <!-- P?-AC? --> | <!-- SC-? --> |
| 12 | WHEN the user switches sessions the main region SHALL load that session's history without a full page reload. | <!-- click another session → assert its first query string appears, no navigation event --> | <!-- P?-AC? --> | <!-- SC-? --> |
| 13 | WHERE a new browser tab is opened the app SHALL start an isolated new session (per-tab isolation). | <!-- open second tab → assert distinct session id --> | <!-- P?-AC? --> | <!-- SC-? --> |

<!-- A raw `<table>` with no sort/row-count, a static chart image, or a decorative (non-clickable)
     chip does NOT satisfy any criterion above. Each row's "Phase AC" MUST cite a PN-ACn in
     delivery-plan.md and "Serves SC" a SC-N in vision.md (bidirectional trace). -->

<!-- ============================ END EXAMPLE BLOCK (criteria 1–13) ============================ -->

---

## Cross-screen interaction contracts

<!-- FILL IN: The behaviours that span screens / live in the shell and would otherwise be invented
     by the executor. Each row is ONE EARS criterion + a runnable acceptance test, OR an explicit
     [ASSUMPTION: value] (never a blank, never a silent default). Pagination/page-size is owned by
     whichever of api.md / data-model.md declares it — cite the owner, do not invent a second one.

     The four rows below are REQUIRED (the executor needs all four); add more as the product needs.
     A blank cell in any required row, or a row defaulted silently without an [ASSUMPTION] tag, is
     REJECTED. -->

| # | Contract | EARS criterion OR [ASSUMPTION: value] | Acceptance test | Phase AC | Serves SC |
|---|----------|---------------------------------------|-----------------|----------|-----------|
| X1 | Pagination / page size | <!-- e.g. cite api.md owner: "page size = 50, server-side (api.md §GET /list)"; OR [ASSUMPTION: client-side, page size 50] --> | <!-- seed >page-size rows → assert rendered rows ≤ page size + a 'next' control --> | <!-- P?-AC? --> | <!-- SC-? --> |
| X2 | Error-toast lifecycle | <!-- e.g. WHEN an error toast shows it SHALL auto-dismiss after N s and ≤K toasts stack (oldest evicted); OR [ASSUMPTION: 6 s, max 3] --> | <!-- fire 4 errors → assert ≤3 toasts in DOM; wait N s → assert toast gone --> | | |
| X3 | Initial paint (Empty CTA vs Loading) | <!-- e.g. WHILE /health is in flight the shell SHALL show the Loading state; once resolved with no prior query it SHALL show the Empty CTA (never a blank main region) --> | <!-- load app cold → assert Loading skeleton, then Empty CTA string visible --> | | |
| X4 | Responsive / narrow-viewport shell | <!-- e.g. WHERE viewport width < {Npx} the session sidebar SHALL collapse to a toggle; OR [ASSUMPTION: desktop-only ≥ 1024px, narrow unsupported] --> | <!-- set viewport 375px → assert sidebar collapsed / toggle present --> | | |

---

## Stub-Mode Banner

<!-- FILL IN: The exact banner shown WHENEVER the backend reports stub_mode:true, so no viewer
     mistakes canned output for real AI. This is a HARD GATE (Stub-banner). Specify trigger,
     placement, the VERBATIM copy string, and the gate that asserts it. The /health shape and the
     stub_mode flag are owned by api.md — reference, do not restate the shape. -->

| Aspect | Specification |
|--------|---------------|
| Trigger | WHILE `GET /health` returns `stub_mode === true` (shape owned by api.md) |
| Placement | full-width, top of **every** screen, rendered on first paint (no scroll, no flash-of-absence) |
| Copy (verbatim) | `STUB MODE — responses are canned, not real AI output` |
| Dismissable? | no — it disappears automatically only when a real LLM key makes `stub_mode === false` |
| Asserted by | the **Stub-banner** + **Live-UI** hard gates (`harness/rules/testing.md`) — banner string found in the rendered DOM of the running frontend origin |

**Criterion (EARS + exact test):**

| # | EARS criterion | Acceptance test (asserted string) | Phase AC | Serves SC |
|---|----------------|-----------------------------------|----------|-----------|
| 14 | WHILE `stub_mode` is true the app SHALL display a full-width top banner reading exactly `STUB MODE — responses are canned, not real AI output` on every screen. | <!-- start frontend in stub mode; assert the verbatim string is present in the rendered DOM at the top region on first paint --> | <!-- e.g. P1-AC2 --> | <!-- SC-? --> |

> **Weak vs Strong:**
> - WEAK: "the app SHALL indicate stub mode." → a tiny grey badge, or nothing on first paint,
>   passes. REJECTED.
> - STRONG: criterion 14 above — the verbatim full-width string asserted in the rendered DOM by
>   the Stub-banner gate. Cannot be hand-waved.

---

## Open questions / assumptions

<!-- FILL IN: Use [NEEDS CLARIFICATION: …] ONLY for architecture-changing UI unknowns (e.g. "does
     the result stream token-by-token or arrive whole?"). Use [ASSUMPTION: value] for everything
     defaulted (e.g. [ASSUMPTION: pagination page size = 50]). Never leave a blank cell, a silent
     default, or a 'TBD'.

     GATE: every defaulted choice surfaced elsewhere in this file (any [ASSUMPTION] in the
     Cross-screen contracts or four-state cells) MUST also appear as a row here, so the user sees
     the full list of defaults in one place. Deleting this section is allowed ONLY when there are
     genuinely zero [NEEDS CLARIFICATION] and zero [ASSUMPTION] rows anywhere in the file; if any
     [ASSUMPTION] exists above, an empty/deleted section is REJECTED. -->

| Item | Type | Detail |
|------|------|--------|
| <!-- e.g. result delivery --> | <!-- NEEDS CLARIFICATION / ASSUMPTION --> | <!-- e.g. [ASSUMPTION: polling, animated 'thinking…' with elapsed seconds] --> |
