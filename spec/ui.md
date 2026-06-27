# UI

## UI Type

Browser-based chat interface with a persistent file-upload sidebar and inline chart rendering. The frontend is a Next.js 15 static export served by the FastAPI backend at `/app/`. See `spec/architecture.md` for the framework and library choices.

---

## Layout

Two-column layout filling the viewport:

- **Left sidebar (280px fixed):** file upload zone + list of ingested tables. Sticky on scroll.
- **Right main area (flex-grow):** chat history (scrollable) + message input at the bottom.

---

## Views / Screens

### Screen: Main (the only screen in Phase 1)

**Purpose:** The single-page workspace where the user uploads data files and asks questions about them.

**Left sidebar — key elements:**
- **App title:** "Data Agent" at the top.
- **File drop zone:** a dashed-border rectangle labelled "Drop CSV or Excel file here, or click to browse". Supports drag-and-drop and click-to-open-file-picker. Accepts `.csv`, `.xlsx`, `.xls` only. Shows a spinner while upload is in progress.
- **Uploaded tables list:** below the drop zone, a list of pills/badges, one per ingested file. Each pill shows the `table_name` and `row_count`. Clicking a pill shows a tooltip with the full column list.
- **[STUB — Phase 2] PostgreSQL connection panel:** a collapsed section at the bottom of the sidebar labelled "Connect PostgreSQL database — Coming in Phase 2". Clicking it shows a disabled form with greyed-out host/port/database/user/password fields and a "Connect (Phase 2)" button.

**Right main area — key elements:**
- **Chat history:** a scrollable list of turns. Each turn consists of:
  - **User bubble:** right-aligned; shows the question text.
  - **Agent bubble:** left-aligned; shows three stacked sections:
    1. **SQL disclosure:** a `<details>` / collapsible block labelled "SQL used". Expanding it shows the `sql_query` in a `<pre>` block with monospace font.
    2. **Prose narrative:** the `output_text` prose, rendered as plain text.
    3. **Charts:** up to 4 Recharts components rendered inline. Each chart has a title derived from `chart_specs[i].title`. If `chart_specs` is empty, no chart section is shown.
- **Empty state:** when no messages exist, a centered placeholder: "Upload a file and ask a question to get started."
- **Message input area:** fixed at the bottom of the main area. Contains a text input and a "Analyze" button. Input is disabled (greyed) when no files have been uploaded yet. Placeholder text: "Ask a question about your data…".

**[STUB — Phase 4] Export button:** a disabled "Export to CSV" button in the top-right corner of the main area, labelled "Export — Coming Later".

---

## Chart Rendering

Charts are rendered client-side only using Recharts. The backend returns `chart_specs` JSON; the frontend maps each spec to the correct Recharts component:

| `chart_type` | Recharts component |
|-------------|-------------------|
| `line` | `LineChart` with `Line` per y-axis entry |
| `bar` | `BarChart` with `Bar` per y-axis entry |
| `histogram` | `BarChart` with pre-computed bins (bins computed client-side from raw data points in `chart_specs.data`) |
| `scatter` | `ScatterChart` with `Scatter` |

All charts are 100% wide, 280px tall. Recharts `ResponsiveContainer` wraps each chart. Axes use the `label` values from `chart_specs.x_axis.label` and `chart_specs.y_axes[i].label`. Tooltip is enabled on all chart types.

---

## Loading and Error States

- **File upload in progress:** the drop zone shows a spinner and "Uploading…" text. The message input is disabled.
- **Analysis in progress:** after the user submits a question, the "Analyze" button is replaced by a spinner labelled "Analyzing…". A skeleton agent bubble is shown in the chat history with an animated pulse to indicate loading.
- **Inline error:** if the API returns an error, an error agent bubble is shown in the chat thread (left-aligned, red border) with the error message text. A "Try again" link is shown below the error.
- **Upload error:** a red inline message appears below the drop zone with the error detail (e.g. "File too large — max 50 MB").

---

## Stubs vs Real (Phase 1)

| Surface | Phase 1 status |
|---------|---------------|
| File drop zone + upload | Real |
| Uploaded tables list (pills) | Real |
| Chat history + question input | Real |
| SQL disclosure block | Real |
| Prose narrative display | Real |
| Recharts inline charts | Real |
| Loading + error states | Real |
| PostgreSQL connection panel (sidebar) | Stub — labelled "Coming in Phase 2" |
| Export to CSV button | Stub — labelled "Coming Later", disabled |

---

## Session Persistence

A session ID is created on first page load (`POST /sessions`) and stored in `localStorage` under the key `data_agent_session_id`. On subsequent loads, the same session ID is reused and the file list is re-fetched from `GET /sessions/{id}/files`. Chat history is stored in React state only — it does not survive a page reload in Phase 1.

> **Assumed:** Chat history is ephemeral (React state) in Phase 1. Persisted conversation history across reloads is deferred to Phase 2 via `GET /sessions/{id}/history`.
