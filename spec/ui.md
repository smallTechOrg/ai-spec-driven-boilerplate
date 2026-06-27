# UI

> Single-page local web app served at `http://localhost:8001/app/`. Same-origin fetch to the JSON API. Phase 1 ships the full vision visually: real UI for upload → ask → answer + chart, plus clearly-labelled NON-FUNCTIONAL stubs for later features so the user sees where it's going (a stub must never look like a bug).

---

## UI Type

Local web app — chat + charts. Next.js 15 static export (React 19), Recharts for charts.

## Views / Screens

### Screen: DataChat (single page)

**Purpose:** Upload data, ask questions, read answers, view charts.

**Key elements:**
- **Upload panel (real, Phase 1):** drag/drop or file-picker for a CSV. On success shows filename, row count, and the detected column list.
- **Chat box + history (real, Phase 1):** a text input to type a plain-English question and a scrollable list of prior Q&A turns.
- **Answer panel (real, Phase 1):** the plain-English answer for the latest question.
- **Chart panel (real, Phase 1):** Recharts render of the returned `chart_spec` (bar in Phase 1; richer types in Phase 3).
- **Privacy badge (real, Phase 1):** a visible "Your data stays on this machine — only summaries are sent to the model" indicator, reinforcing the core promise.
- **Labelled stubs (NON-FUNCTIONAL in Phase 1, each marked "Coming soon"):**
  - **Connect PostgreSQL** — a disabled/notice form (real in Phase 2).
  - **Switch dataset / multi-dataset** — a disabled selector (later).
  - **Download report** — a disabled button (real in Phase 3).
  - **Detect anomalies** — a disabled control (real in Phase 5).

**Actions available:**
- Upload a CSV (real).
- Type and submit a question (real).
- View answer + chart (real).
- (Stubs render but are visibly disabled with a "Coming soon" label.)

## Error States

- **Loading:** spinner/disabled submit while `/ask` or `/datasets` is in flight.
- **Empty:** before any upload, a friendly prompt to upload a CSV; chat disabled until a dataset exists.
- **Error:** `api_error` responses surfaced inline (e.g. "Couldn't reach the model — try again" for `LLM_UNAVAILABLE`; "Couldn't read that file" for `BAD_UPLOAD`). Stubs never surface errors — they are inert by design.

## Tech Stack

Next.js 15 + React 19, static export served from `frontend/out` at `/app`; Recharts for charts; same-origin `fetch` to the FastAPI JSON API. Built against the contract in [api.md](api.md).
