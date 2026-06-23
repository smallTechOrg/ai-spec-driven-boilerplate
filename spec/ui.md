# UI

---

## UI Type

Single-page web dashboard (Next.js 15 + React 19, Tailwind), static-exported and served by FastAPI at `/app`. Test URL: **http://localhost:8001/app/**. Single origin, so the browser calls `/datasets`, `/ask`, `/audit` directly (relative paths).

## Layout

One page (`frontend/src/app/page.tsx`) titled **"Data Analyst"**, arranged as:

- Left column: **Datasets** (upload + list).
- Center column: **Ask a question** (input + result).
- Lower / right: **Audit Log** (table + export).
- A **"Coming soon"** row of clearly-labelled stub cards: Charts, Dashboards, Cross-Dataset Query.

## Views / Screens

### Screen: Datasets (REAL in Phase 1)

**Purpose:** Upload data and pick which dataset to query.
**Key elements:**
- File picker (accepts `.csv`, `.xlsx`) + **Upload** button → `POST /datasets`.
- Dataset list (`GET /datasets`): each shows name, row count, and a collapsible column schema (name + type).
- Selecting a dataset sets it as the active target for the Ask box.
**Actions:** Upload a file; select a dataset.

### Screen: Ask a question (REAL in Phase 1)

**Purpose:** Ask one NL question over the selected dataset.
**Key elements:**
- Text input + **Ask** button → `POST /ask` with `{dataset_id, question}`.
- **Result:** a narrative paragraph (senior-analyst tone) above a formatted result table (`columns` + `rows`), with a small footer showing `row_count` and `duration_ms`.
- A collapsible **"Show SQL"** disclosure revealing `sql` (transparency).
**Actions:** Type a question; submit; expand SQL.

### Screen: Audit Log (REAL in Phase 1)

**Purpose:** Review and export every operation.
**Key elements:**
- Table (`GET /audit`): timestamp, question, SQL (truncated, expandable), row count, duration, status.
- **Export** button → `GET /audit/export?format=csv` (download).
- Refreshes after each ask; rows persist across restarts (demonstrated by reloading after a server restart).
**Actions:** View entries; export.

### Screen: Coming-soon stubs (NON-FUNCTIONAL — labelled, NOT bugs)

**Purpose:** Show the product vision without faking functionality.
**Key elements:** Three cards — **Charts**, **Dashboards**, **Cross-Dataset Query** — each with a muted "Coming soon" badge, a one-line description, and disabled/non-interactive controls. They are visually distinct (dimmed, badge) so they read as intentional placeholders.
**Actions:** None (intentionally inert).

## Error States

- **Upload error** (400/500): inline red banner on the Datasets panel with the server message (e.g. "Unsupported file type").
- **Ask error** (400/502/500): red banner under the Ask box ("The model couldn't generate valid SQL for that question — try rephrasing." for 400; "Analysis service is temporarily unavailable — please retry." for 502). The failed attempt still appears in the Audit Log with status `failed`.
- **Loading:** Upload shows a spinner on the button; Ask shows "Analyzing…" and disables the button; lists show a skeleton/placeholder while fetching.
- **Empty:** "No datasets yet — upload a CSV or Excel file to begin." / "Ask a question to see results." / "No operations logged yet."

## Tech Stack

Next.js 15 + React 19 + Tailwind CSS, static export (`output: 'export'`, `basePath: '/app'`), built with `pnpm build` into `frontend/out`, served by FastAPI at `/app`.
