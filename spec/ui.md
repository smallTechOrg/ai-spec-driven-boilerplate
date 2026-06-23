# UI

## UI Type

Single-page web application served at `http://localhost:8001/app/`. Three-column-ish layout: a fixed left sidebar for dataset management and a wide main area split between a query panel and an audit/stub area.

## Session Handling

- On first page load: generate a UUID v4, store as `localStorage.analyst_session_id`.
- On subsequent loads: read `localStorage.analyst_session_id`; use the stored value.
- Every API call sends the session ID as the `X-Session-ID` request header.
- The session ID is never exposed beyond the footer label (first 8 chars).
- No session expiry logic in Phase 1.

---

## Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Data Analyst                                          [Audit]           │
├─────────────────┬────────────────────────────────────────────────────────┤
│  SIDEBAR (240px)│  MAIN AREA                                             │
│                 │  ┌──────────────────────────────────────────────────┐  │
│  [Upload ▲]     │  │ QUERY INPUT                                      │  │
│  ─────────────  │  │  [Ask a question about your data…]   [Send]      │  │
│  sales.csv      │  └──────────────────────────────────────────────────┘  │
│  1,234 rows     │  ┌──────────────────────────────────────────────────┐  │
│  Jun 23 10:05   │  │ RESPONSE PANEL (scrollable)                      │  │
│                 │  │  [markdown answer text]                          │  │
│  orders.xlsx    │  │  [HTML table]                                    │  │
│  500 rows       │  └──────────────────────────────────────────────────┘  │
│  Jun 23 10:10   │  ┌─────────────────┐ ┌──────────────────────────────┐  │
│                 │  │ Charts          │ │ Dashboards                   │  │
│                 │  │ coming in       │ │ coming in Phase 3            │  │
│                 │  │ Phase 2  [stub] │ │ [stub]                       │  │
│                 │  └─────────────────┘ └──────────────────────────────┘  │
├─────────────────┴────────────────────────────────────────────────────────┤
│  Session: 550e8400                                                       │
└──────────────────────────────────────────────────────────────────────────┘
```

When the Audit tab is active, the main area is replaced by the audit table (sidebar stays visible).

---

## Components

### `Sidebar.tsx`

**Responsibility:** Dataset list + upload button. Always visible (240px fixed width).

**Elements:**
- "Upload" button at top. Clicking opens a native file picker (`<input type="file" accept=".csv,.xlsx">`).
- On file selection: POST to `/datasets/upload` with `X-Session-ID` header and `multipart/form-data`. Show a spinner on the button during upload. On success: add the dataset to the list. On error: show a red error message below the button (dismiss on next upload attempt).
- Dataset list (newest first): each entry shows `original_filename`, `row_count` (formatted with commas, e.g. "1,234 rows"), and `created_at` (date only, e.g. "Jun 23 10:05"). Clicking a dataset entry selects it (highlights it and populates `dataset_table` for the next query — the last-clicked dataset is used when the user sends a query).
- Empty state: "No datasets yet. Click Upload to get started."
- On mount: call `GET /datasets` with `X-Session-ID` to populate the list.

**State:** `datasets: Dataset[]`, `selectedTable: string | null`, `uploading: boolean`, `uploadError: string | null`

---

### `QueryPanel.tsx`

**Responsibility:** Chat-style query input and response area.

**Elements:**
- **Query input row** (pinned at top of main area):
  - Text input field, placeholder "Ask a question about your data…"
  - "Send" button. Disabled when: no dataset selected, input is blank, or a query is in flight.
  - On Send: POST to `/query` with `{question, dataset_table}` body and `X-Session-ID` header. Show loading state ("Thinking…" label on the button, input disabled).
- **Response panel** (scrollable area below input):
  - On success: render `answer` as markdown (using a lightweight renderer — no full MDX, just bold/italic/lists/code spans). Below the markdown, render the `table` as an HTML `<table>` with column headers from the dict keys of the first row. Show the SQL in a collapsed `<details>` element ("Show SQL").
  - On error: red alert box with the `error` string from the 502 response.
  - Empty state: "Select a dataset from the sidebar and ask a question."
  - Each query-response pair is shown in sequence (most recent at the bottom). Previous pairs are kept in the UI (not cleared on new query).

**State:** `question: string`, `loading: boolean`, `responses: QueryResponse[]`

---

### `AuditTab.tsx`

**Responsibility:** Audit log table. Shown when the "Audit" tab in the header is active (replaces the main area content).

**Elements:**
- Header: "Audit Log"
- Table columns: Timestamp (created_at, formatted as local datetime), Dataset (original_filename looked up from dataset_table), Question (truncated to 60 chars with ellipsis), Rows (row_count or "—"), Duration (duration_ms + "ms" or "—"), Status ("ok" in green if error is null, "error" in red if error is non-null).
- Sorted newest first.
- On mount / on tab activate: call `GET /audit` with `X-Session-ID`.
- Empty state: "No queries yet. Ask a question to see the audit log."
- Error entries show red "error" badge in the Status column; hovering shows the error string in a tooltip.

**State:** `entries: AuditEntry[]`, `loading: boolean`

---

### `StubCard.tsx`

**Responsibility:** Reusable placeholder card for unbuilt features.

**Props:** `title: string`, `comingSoon: string`

**Renders:** A grey-bordered card with the `title` and a muted label `"coming in {comingSoon}"`. No interactivity. Clearly visually distinct from functional components (dashed border, italic text).

Used for:
- Charts stub: `<StubCard title="Charts" comingSoon="Phase 2" />`
- Dashboards stub: `<StubCard title="Dashboards" comingSoon="Phase 3" />`

---

### `page.tsx`

**Responsibility:** Root page. Composes all components. Manages global state: session ID, active tab, selected dataset.

**Active tab logic:** `activeTab: "query" | "audit"`. Header bar "Audit" button toggles between tabs. When `activeTab === "audit"`, the `AuditTab` replaces the query/response area. The sidebar is always visible.

**Session bootstrap on mount:**
1. Read `localStorage.analyst_session_id` or generate a new UUID v4 and write it.
2. Call `GET /datasets` with `X-Session-ID` to hydrate the sidebar.

---

## Header Bar

Fixed at top across full width.

- Left: "Data Analyst" title (bold).
- Right: "Audit" tab button. Active state: underlined or filled variant.

---

## Footer

Single line at the bottom: `Session: {first 8 chars of session_id}`.

---

## Styling

Tailwind CSS v4. Clean professional appearance. No custom colour theme — use Tailwind defaults (slate/grey palette). Responsive to viewport width ≥ 1024px; no mobile breakpoints required in Phase 1.

`postcss.config.mjs` must contain `{ plugins: { '@tailwindcss/postcss': {} } }` for Tailwind v4 utility generation.

---

## Build Notes

- `next.config.js`: `output: 'export'`, `basePath: '/app'`
- All API calls use absolute paths from the origin root (e.g. `/datasets/upload`, `/query`, `/audit`) — single-origin, no CORS.
- `NODE_OPTIONS=--no-experimental-webstorage` in `package.json` scripts (Node ≥25 safety).
- Static export lands in `frontend/out/`; FastAPI mounts it at `/app`.

---

## Error States

| Error scenario | UI treatment |
|---------------|--------------|
| Upload fails (422/500) | Red text below the Upload button: "Upload failed: {message}". Clears on next upload attempt. |
| Query fails (502) | Red alert in the response panel: "Could not answer: {error}". |
| Audit fetch fails | Red text in the audit table area: "Could not load audit log." with a Retry button. |
| No dataset selected when sending query | "Send" button is disabled; input shows tooltip "Select a dataset first." |

## Loading States

| State | Indicator |
|-------|-----------|
| Dataset list loading on mount | Skeleton rows in sidebar |
| File uploading | Spinner on Upload button |
| Query in flight | "Thinking…" label on Send button; input disabled |
| Audit loading | Skeleton rows in audit table |
