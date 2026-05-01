# Vision — Sourcing Agent (Construction Materials)

## What This Agent Does

The Sourcing Agent helps real-estate / construction project teams source raw
materials (bricks, cement, steel, sand, etc.). Given a sourcing request — material
type, quantity, location, budget, timeline, and quality criteria — the agent
researches potential suppliers on the web, normalizes their offerings, scores
each one against the user's criteria, and returns a ranked recommendation report
with rationale and source links.

## Who Uses It

- **Procurement managers** at small-to-mid-size construction / real-estate firms.
- **Site managers / project leads** who need a shortlist of credible suppliers
  fast, without spending half a day in IndiaMART tabs.

## Core Problem Being Solved

Material sourcing today is manual web-search + spreadsheets + phone calls. The
buyer juggles 5–10 supplier directories, copies prices into a sheet, and tries
to remember which supplier had MOQ vs. quality vs. delivery trade-offs. The
agent collapses that into a single request → ranked report flow with the
trade-offs made explicit.

## Success Criteria

- [ ] User submits a sourcing request via web form and gets a ranked supplier
      report within ~60 seconds.
- [ ] Each recommendation includes: supplier name, location, indicative
      price/unit, lead time, and a one-paragraph rationale.
- [ ] Each recommendation cites at least one source URL.
- [ ] The full pipeline runs offline (stub LLM + stub search) and renders a
      believable demo report — every page shows a clear "stub mode" banner
      whenever the real provider is not configured.
- [ ] Run history persists in PostgreSQL and is replayable from a run ID.

## What This Agent Does NOT Do (Out of Scope for v0.1)

- No multi-material requests in one run (one material per request).
- No supplier dedup across runs / persistent supplier knowledge base.
- No outreach (no RFQ emails, no phone calls, no negotiation).
- No transactional features (no orders, no payments, no contracts).
- No authentication / multi-tenant. Single-user local app.
- No scheduled re-runs or alerts.

## Key Constraints

- **Stack:** Python 3.12, PostgreSQL, FastAPI/Jinja2, LangGraph. No SPA.
- **APIs:** Gemini for LLM, Tavily for search. Both must have working stub
  providers so the app is demo-able with zero keys.
- **Latency:** Whole pipeline target < 90s per request on stub mode; real-mode
  bounded by Tavily + Gemini.
- **Budget:** Cap to ~5 Tavily searches and ~3 Gemini calls per run in v0.1.

## Phases of Development

| Phase | Description | Success Gate |
|-------|-------------|--------------|
| 1 | Domain models, DB schema, Alembic migration, repository CRUD | `uv run pytest tests/unit` 100% pass against PostgreSQL; `uv run alembic current` non-blank |
| 2 | Stubbed LangGraph loop end-to-end + web UI + README | `uv run pytest` 100% pass; golden-path UI smoke test green; live-server `/health` and `/` return 200 |
| 3 (future) | **Richer supplier dossier + tabular report + live run progress** (see capability spec) | Each supplier has reviews / feedback / delivery / solvency signals; report is a sortable table; user sees node-level progress while the run executes |
| 4 (future) | Real Tavily + Gemini integration, scoring tuned on real data | Manual eval on 3 real requests |
| 5 (future) | Multi-material requests + supplier dedup | TBD |

## Future Phases (deferred from v0.1)

- **Phase 3 — supplier dossier + tabular report + live progress** (specced in
  `spec/product/capabilities/03-supplier-dossier.md`):
  - Enrich each supplier with: Google reviews (rating + count), aggregated
    customer feedback summary, delivery reliability signal (on-time %, lead-time
    variance), solvency / business-stability signal (years in business, GST /
    registration status, credit signals where public).
  - Report renders as a **sortable table** (one row per supplier, columns for
    each signal + score) instead of stacked cards — easier to compare side by
    side.
  - During a run, the UI shows **node-level progress** (research → enrich →
    score → finalize) via Server-Sent Events or short polling, so the user can
    see what the agent is doing instead of staring at a spinner.
- Multi-material concurrent sourcing.
- Persistent supplier knowledge base + dedup across runs.
- RFQ email drafting + response tracking.
- Scheduled re-sourcing (price/availability watch).
- Auth + multi-org.
