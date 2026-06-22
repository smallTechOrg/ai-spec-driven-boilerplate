# UI

## UI Type

Browser-based single-page chat interface. Vanilla HTML/JS, no build step. Served by FastAPI as static files from `frontend/index.html`. All API calls use the browser `fetch` API.

---

## Layout

The page is divided into two panels side by side:

```
┌────────────────────────────────────────────────────────────┐
│  Data Analyst Agent                              [health ●] │
├───────────────────┬────────────────────────────────────────┤
│  DATASETS         │  CHAT                                  │
│  ─────────────    │  ─────────────────────────────────     │
│  [+ Upload File]  │  [Welcome message / empty state]       │
│                   │                                        │
│  • sales_q1       │  User: What were the top 5 products?   │
│    4,821 rows     │                                        │
│    [delete]       │  Agent: ## Top 5 Products              │
│                   │  | Product | Revenue |                 │
│  • employees      │  | ...     | ...     |                 │
│    312 rows       │  ...                                   │
│    [delete]       │  **You might also ask:**               │
│                   │  - ...                                 │
│                   │                                        │
│                   │  [────────── text input ──────────]    │
│                   │                           [Send]       │
└───────────────────┴────────────────────────────────────────┘
```

---

## Views / Screens

### Screen: Main Page (Single Page)

**Purpose:** The entire application lives on one page. No navigation or routing.

**Left sidebar — Dataset Catalogue:**

- Header: "Datasets"
- Upload widget (always visible at the top of the sidebar):
  - `[+ Upload File]` button that opens a native file picker (accepts `.csv`, `.xlsx`, `.xls`)
  - After file is selected: a small inline form appears with a `Name` text input (pre-filled with the filename without extension), an optional `Description` textarea, and a `[Upload]` confirm button
  - While uploading: button is disabled, spinner shown, text reads "Uploading..."
  - On success: form collapses; new dataset appears at top of list
  - On error: inline error message shown below the form (e.g., "File too large", "Unsupported format")
- Dataset list:
  - Each item shows: dataset `name` (bold), `row_count` formatted with commas (e.g., `4,821 rows`), and a small `[×]` delete icon
  - Clicking the name shows the schema columns in a collapsible panel below the item
  - Schema panel: table with two columns — Column Name, Type
  - Clicking `[×]` shows a confirmation prompt (`"Remove <name> from catalogue?"`) then calls DELETE `/datasets/{id}` and removes the item from the list
- Empty state: "No datasets yet. Upload a CSV or Excel file to get started."

**Right panel — Chat:**

- Header: "Chat" with the active `session_id` shown in small muted text (for debugging)
- Message thread:
  - User messages: right-aligned, plain text bubble
  - Assistant messages: left-aligned, rendered as markdown (using a lightweight markdown renderer such as `marked.js`, included via CDN — no build step)
  - Markdown tables are rendered as HTML `<table>` elements with basic styling
  - Timestamps shown below each message in muted text (local time)
- Empty state: centred welcome message: "Upload a dataset and ask a question to get started."
- Input area (pinned to bottom):
  - Multi-line `<textarea>` that auto-expands up to 5 lines; `Enter` submits, `Shift+Enter` inserts newline
  - `[Send]` button
  - While the agent is processing: textarea and button are disabled; a typing indicator (three animated dots) appears in the message thread as a placeholder assistant message
  - On error: the placeholder is replaced with an error message in red: "Something went wrong. Please try again."

**Health indicator (top-right header):**

- A coloured dot: green when `GET /health` returns `status: ok`, red otherwise
- Checked on page load and every 30 seconds

---

## Interactions

| Interaction | Trigger | Behaviour |
|-------------|---------|-----------|
| Upload file | Click `[+ Upload File]` | Opens file picker; after selection shows inline form |
| Confirm upload | Click `[Upload]` | POST `/datasets` (multipart); show spinner; on 201 add to sidebar list |
| Expand schema | Click dataset name | Toggle collapsible schema panel below the item |
| Delete dataset | Click `[×]` → confirm | DELETE `/datasets/{id}`; remove item from sidebar list |
| Send message | Click `[Send]` or press `Enter` | POST `/chat`; show typing indicator; render response on arrival |
| New session | First message sent | `session_id` is null in first request; server returns new ID; stored in `sessionStorage` |
| Restore session | Page reload | `session_id` read from `sessionStorage`; GET `/sessions/{id}/history` to reload chat thread |
| Health check | Page load + every 30 s | GET `/health`; update indicator dot colour |

---

## Error States

| Scenario | User-visible behaviour |
|----------|------------------------|
| Upload: file too large (413) | Inline error below upload form: "File too large (max 200 MB)." |
| Upload: unsupported type (415) | Inline error: "Unsupported file type. Please upload a CSV or Excel file." |
| Upload: parse error (422) | Inline error: "Could not read the file. Check that it is a valid CSV or Excel file." |
| Chat: Gemini API error (502) | Error message in chat thread: "The AI service is unavailable. Please try again shortly." |
| Chat: no matching dataset | Agent's own response (narrative) explains no relevant data was found |
| Chat: session not found (404) | Alert banner: "Session expired or not found. Starting a new session." — clears `sessionStorage` and starts fresh |
| Health check fails | Health dot turns red; no blocking modal — user can still interact |
| Network offline | `fetch` error caught; inline error: "Network error. Check your connection." |

---

## Notes

- No authentication UI — no login screen, no user accounts.
- No chart rendering — result tables are HTML tables only.
- No dark mode — basic light-mode styling only for v1.
- The markdown renderer (`marked.js`) is loaded from CDN. If CDN is unavailable, raw markdown is shown as plain text (degraded but not broken).
- The frontend stores only `session_id` in `sessionStorage` (cleared on tab close). No other client-side state is persisted beyond the page lifetime; all data lives in the server's SQLite.
