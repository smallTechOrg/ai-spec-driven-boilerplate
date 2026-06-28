# UI

The single-page workspace for the Local Data Analyst. Visually complete in Phase 1: real UI for the one working path (upload → profile → ask → rich answer) PLUS clearly-LABELLED non-functional stubs for everything coming later. A stub must never read as a bug — every stub shows a "Coming soon" badge.

---

## UI Type

Single-page web workspace. Next.js 15 static export (`output: 'export'`, `basePath: '/app'`) + React 19 + Tailwind v4, served by FastAPI at `http://localhost:8001/app/`. Charts via Recharts. Calls the REST API in [api.md](api.md). All logic is client-side fetch; no SSR (static export).

## Layout

A two-pane workspace: a left **library sidebar** (mostly stubbed in Phase 1) and a main **workspace column** (upload + profile + question + answer). A top bar shows the app name and a **daily-cost total** (stub in Phase 1).

## Views / Screens

### Screen: Workspace (the only screen)

**Purpose:** The user loads a file, sees its profile, asks questions, and reads rich answers with full transparency.

**Key elements (REAL in Phase 1):**
- **Upload / drag-drop area** — drag a CSV/Excel file or click to pick. On drop, calls `POST /api/datasets`, shows a loading state, then renders the profile card. Ships with a hint pointing at `samples/sample_sales.csv`.
- **Dataset profile card** — auto-shown after upload: row count, column names + types, null counts, basic per-column stats. (Auto-profile on load — the user does nothing extra.)
- **Question box** — a text input + submit. Calls `POST /api/ask` with the active `dataset_id`. Disabled until a dataset is loaded.
- **Rich-answer view** — renders the `/api/ask` envelope:
  - plain-language **answer** (prominent),
  - **key-stat callouts** (the `key_stats[]` as cards),
  - **chart** (Recharts, driven by `chart_spec`),
  - **summary table** (`summary_table`),
  - **written insight** (`insight`).
- **Expandable "Code / Steps / Profile" panel** — collapsed by default; expands to show `plan_steps`, the exact `generated_sql`, and the dataset profile.
- **Per-query cost** — shows `cost.prompt_tokens` + `cost.completion_tokens` + `cost.est_usd` for the answer.

**Key elements (LABELLED STUBS in Phase 1 — each shows a "Coming soon" badge):**
- **Library sidebar** — shows the current dataset and a disabled "Add to library / switch dataset" list (real in Phase 2).
- **Watched-folder control** — a disabled "Watch a folder" panel (real in Phase 4).
- **Multi-file join / dataset picker** — a disabled "Join datasets" control (real in Phase 3).
- **Session-restore banner** — a disabled "Resume previous session" affordance (real in Phase 2).
- **Daily-cost total** (top bar) — shows the current query's cost with a "daily total coming soon" note (real in Phase 5).
- **Follow-up chips** — the `follow_ups[]` are rendered as chips but are **display-only in Phase 1** (clicking is wired in Phase 4); labelled "suggestions (preview)".
- **Reproducible re-run** — a disabled "Re-run" affordance on the (future) history list (real in Phase 5).

**Actions available (Phase 1):**
- Upload a file (drag-drop or picker).
- Type and submit a question.
- Expand/collapse the code/steps/profile panel.

## Error States

- **Loading:** upload and ask both show a spinner/skeleton; the question box disables during an in-flight ask.
- **Empty:** before any upload, the workspace shows a friendly "Drop a CSV or Excel file to begin (try samples/sample_sales.csv)" empty state.
- **Upload error:** unsupported type / too large / parse failure → an inline error banner with the `error.message` from `api_error`.
- **Ask error / failed run:** when `/api/ask` returns `status: "failed"`, the UI shows the error message AND the attempted `generated_sql` in the code panel, so the user sees what was tried (never a silent failure).
- **Network error:** "Network error — is the server running?" banner.
- **Stub clarity:** every stubbed control is visibly disabled with a "Coming soon" badge so it is never mistaken for a broken feature.

## Tech Stack

Next.js 15 + React 19 + Tailwind v4 (static export, served at `/app/`), Recharts for charts. Files under `frontend/src/`: `app/page.tsx` (the workspace), `components/*.tsx` (UploadArea, ProfileCard, QuestionBox, RichAnswer, KeyStats, ChartView, SummaryTable, CodePanel, CostBadge, LibrarySidebar [stub], FollowUps [display-only], plus stub components), `lib/api.ts` (typed fetch helpers matching [api.md](api.md)).
