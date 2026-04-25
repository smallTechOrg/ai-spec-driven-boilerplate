# Capability — Supplier Dossier, Tabular Report, Live Progress (Phase 3)

> **Status:** specced, not implemented. Targets Phase 3.

## Why

v0.1 returns a thin supplier card (name, location, price hint, lead time,
rationale). For real procurement decisions the buyer needs trust signals
(reviews, reliability, solvency) and a side-by-side comparison view. They
also need to know the agent is actually doing something while the run
executes (currently the page just spins for ~30s in real mode).

## Three changes

### 1. Richer supplier dossier

Extend `Supplier` with the following signal fields (all optional, gracefully
absent when the source doesn't yield data):

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `google_rating` | float | Google Maps / Places (Tavily-discovered) | 0.0–5.0 |
| `google_review_count` | int | Google Maps | |
| `feedback_summary` | text | Gemini synthesis of public reviews / forums | One paragraph; cite top 2–3 themes |
| `delivery_reliability` | text | Gemini synthesis of reviews + listings | "high / mixed / unknown" + 1-line rationale |
| `years_in_business` | int | LLM extraction from listings | When derivable |
| `solvency_signal` | text | LLM synthesis (GST / registration / credit hints) | "stable / unclear / weak" + 1-line rationale |
| `gst_registered` | bool \| None | LLM extraction | India-specific |

Add **two new graph nodes** between `enrich` and `score`:

- `gather_signals` — for each supplier, run a targeted Tavily query
  (`"<supplier name>" reviews OR feedback OR delivery`) and collect snippets.
- `synthesize_dossier` — call Gemini once per supplier (or batched) with a
  `<node:dossier>` tag; parse JSON into the new fields.

Stub variants must produce believable values per supplier (deterministic from
name hash, like the current stub) so offline demos still show a credible
table.

Scoring then uses the dossier fields explicitly in the prompt — this should
materially improve rationales.

### 2. Tabular report

Replace the stacked-card report on `/runs/{id}` with a sortable HTML table
(one row per recommendation, sorted by `rank` initially):

| Rank | Supplier | Location | Price | Lead time | Reviews | Reliability | Solvency | Score | |
|------|----------|----------|-------|-----------|---------|-------------|----------|-------|--|
| 1 | Acme Bricks | Bangalore | ₹6.50 / brick | 5–7 days | 4.3 ★ (124) | high | stable | 87 | [details ▾] |

Click "details" to expand an inline panel with the rationale paragraph,
feedback summary, and source URL.

Client-side sorting via a tiny vanilla-JS script (no framework). Default sort
by `score` desc.

### 3. Live run progress

Currently `POST /requests` invokes `run_agent()` synchronously and only
redirects on completion. Replace with:

- `POST /requests` — creates `SourcingRequest` + `Run` rows (status `pending`),
  enqueues the run on a background thread, redirects immediately to
  `/runs/{run_id}`.
- The run thread updates `runs.status` and writes per-node progress events to
  a new `run_events` table: `{run_id, node, status, message, created_at}`.
  Status values: `started`, `completed`, `failed`.
- `/runs/{run_id}` polls `GET /runs/{run_id}/events` (JSON) every ~1s while
  `run.status` is `running`, rendering a progress strip:

  ```
  ✓ Research (5 suppliers found)   ✓ Enrich   ⟳ Score …   ·  Finalize
  ```

  When `run.status` becomes `completed` or `failed`, polling stops and the
  table replaces the strip.

(SSE would be cleaner but polling keeps the stack tiny — no extra deps, works
through any proxy.)

## Migrations / data model deltas

- `suppliers`: add seven new nullable columns listed in §1.
- new table `run_events(id, run_id, node, status, message, created_at)`.
- `runs.status` already supports `pending` / `running` — no change.

## Stub-mode rules (still apply)

- `<node:dossier>` is the new tag for the synthesis call.
- Stub dossier output is deterministic from supplier name hash — same fields,
  realistic-looking values, no cross-contamination with `<node:enrich>` /
  `<node:score>`.
- Stub-mode banner stays visible.

## Out of scope (still)

- Real Google Places API integration (use Tavily-discovered snippets in v0.3;
  swap to Places API in a later phase).
- Persisted supplier dedup across runs.
- Authenticated review-portal scraping.
