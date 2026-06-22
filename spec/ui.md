# UI

Next.js 15 + React 19 chat application. Backend at port 8001.

## Screen: Chat (single screen, Phase 1)

Layout: left **sidebar** (datasets + sessions), main **chat panel**.

### Sidebar
- **Datasets section** — list of uploaded datasets (name + row count). **"Upload CSV"** button (real, functional) → opens file picker → `POST /datasets`. On success the dataset appears here.
- **"Add another dataset (coming soon)"** — visible, **disabled stub** (Phase 3 multi-dataset).
- **Sessions section** — list of sessions; clicking one loads its history (`GET /sessions/{id}/messages`). New-session button creates one. Sessions persist across reloads.
- **"Audit log (coming soon)"** — visible, **disabled stub** (Phase 5).

### Chat panel
- **Message list** — user and assistant messages in order. Assistant messages render:
  - the **formatted text answer** (prose),
  - a **result table** (`columns` + `rows`), scrollable,
  - a small **"View SQL"** disclosure showing the executed query.
- **Composer** — text input + send → `POST /sessions/{id}/query` with the selected `dataset_id`. Loading state while the agent runs.
- **"Chart (coming soon)"** and **"Dashboard (coming soon)"** — visible, **disabled stub** controls near each result (Phase 2).

## Stub labelling

Every non-Phase-1 surface is rendered greyed/disabled with an explicit "(coming soon)" label so it is never mistaken for a bug:
- Add another dataset → Phase 3
- Chart / Dashboard → Phase 2
- Audit log → Phase 5

## States

- **Empty:** no dataset uploaded → composer disabled with hint "Upload a CSV to start."
- **Loading:** spinner in the assistant slot while querying.
- **Error:** `QUERY_FAILED` → assistant bubble shows a friendly error ("I couldn't answer that — the query failed.") plus the surfaced `error` detail; never a blank/hung UI.

## Real vs stub (Phase 1)

| Surface | Phase 1 |
|---------|---------|
| Upload CSV, dataset list | **Real** |
| Session list + persistence | **Real** |
| Ask question → answer + table + View SQL | **Real** |
| Charts / Dashboards / Audit / Add-another-dataset | **Labelled stubs** |
