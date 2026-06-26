# UI

## UI Type

Single-page web application (Next.js static export). Two logical panels on one page: an upload panel on the left/top and a chat panel on the right/bottom. No separate routes needed. The two-panel layout persists across all phases.

---

## Views / Screens

### Screen: Main Page (`/app/`)

**Purpose:** The single working surface. The user uploads a CSV and then asks natural-language questions about it.

---

#### Upload Panel (`components/UploadPanel.tsx`) — REAL in Phase 1

**Key elements:**
- File picker: drag-and-drop zone or "Browse" button. Accepts `.csv` only. Shows the selected filename once chosen.
- "Upload" button: enabled only when a file is selected and no upload is in progress.
- Loading state: spinner replaces the button while upload is in progress.
- Schema preview: after a successful upload, shows the `session_id` (truncated) and a two-column list of column names + dtypes (e.g. `product_name object`, `revenue float64`).
- Row count: "1,500 rows loaded" shown below the schema list.
- Error state: a red alert box with the error message if upload fails.

**Actions:**
- Select file → shows filename
- Click "Upload" → calls `POST /sessions` → shows schema on success, red alert on failure

---

#### Chat Panel (`components/ChatPanel.tsx`) — REAL in Phase 1

**Purpose:** Accept a natural-language question and display the answer inline. Multiple questions accumulate as a scrolling thread.

**Key elements:**
- Disabled state: before a CSV is uploaded, the question input and "Ask" button are greyed out with placeholder text "Upload a CSV file first."
- Question input: single-line text field, max 2000 characters, with a character counter (e.g. "148 / 2000").
- "Ask" button: enabled only when a file is uploaded and the input is non-empty and not at the character limit.
- Loading state: a "Thinking…" spinner card appears at the bottom of the thread while the pipeline runs.
- Answer cards: each question/answer pair appears as a card in the thread (newest at bottom).

**Actions:**
- Type a question → "Ask" button enables; character counter updates
- Submit question → calls `POST /sessions/{session_id}/questions` → shows AnswerCard on success

---

#### Answer Card (`components/AnswerCard.tsx`) — partial in Phase 1, complete in Phase 2

Each answer card contains these sections, visually separated:

1. **Question section:** The question text, displayed at the top of the card in bold.

2. **Answer section (REAL in Phase 1):** Plain-text answer paragraph from the Gemini response.

3. **Chart panel (NON-FUNCTIONAL STUB in Phase 1 / REAL in Phase 2):**
   - Phase 1: a greyed-out placeholder box labelled "Chart — Coming in Phase 2", rendered in `bg-gray-100` with a `StubBadge` component.
   - Phase 2: an `<img>` element with `src={`data:image/png;base64,${chart_base64}`}` and `alt={chart_type + " chart"}`. If `chart_base64` is null, the Phase 1 stub remains.

4. **Code panel (NON-FUNCTIONAL STUB in Phase 1 / REAL in Phase 2):**
   - Phase 1: a greyed-out placeholder box labelled "Executed Code — Coming in Phase 2", rendered in `bg-gray-100` with a `StubBadge`.
   - Phase 2: a syntax-highlighted `<pre><code>` block showing `executed_code`. If `executed_code` is null, the Phase 1 stub remains.

5. **Node trace section (NON-FUNCTIONAL STUB in Phase 1 / REAL in Phase 2):**
   - Phase 1: greyed-out label "Reasoning Trace — Coming in Phase 2" with a `StubBadge`.
   - Phase 2: a collapsible `<details>` element listing the nodes from `node_trace` in order (e.g. "parse_csv → generate_code → execute_code → answer_question → finalize").

---

#### `StubBadge` Component (`components/StubBadge.tsx`)

Renders a small grey pill: `[Coming in Phase N]`. Used by any stub element. Props: `phase: number`.

---

## Error States

| State | Presentation |
|-------|-------------|
| Upload fails (413 / 422) | Red alert box below the upload button with `error.message`. "Try again" link resets the upload panel. |
| Question pipeline fails (`status: "failed"`) | Answer card appears with an amber background and the `error` string. Answer, chart, and code sections are omitted. |
| Network error (fetch throws) | Red alert box: "Network error — is the server running at `http://localhost:8001`?" |
| Session not found (404 from questions endpoint) | Alert: "Session not found. Please re-upload your CSV." Upload panel resets. |
| Question too long (client-side) | Character counter turns red at limit; "Ask" button disables. |

---

## Loading / Empty States

| State | Presentation |
|-------|-------------|
| No CSV uploaded | Chat panel shows grey placeholder: "Upload a CSV file to get started." Question input and Ask button disabled. |
| Upload in progress | Button replaced by spinner; file picker disabled. |
| Question in progress | "Thinking…" spinner card at bottom of chat thread; question input disabled until response arrives. |

---

## Stub Labelling Convention

Every stub element must be visibly non-functional to a first-time user:

- Rendered in grey (`text-gray-400`, `bg-gray-100`, `opacity-50`)
- Displays a `StubBadge` with the phase it arrives in
- Never hidden — the user should see the future shape of the UI, not be confused by missing panels
- Clicking a stub element shows no action (no toast, no navigation) — it is a passive placeholder

---

## Frontend Run Path

The single-origin run path (build → serve via FastAPI) is the canonical path for testing:
1. `cd frontend && pnpm build` — produces `frontend/out/`
2. `uv run python -m src` — starts FastAPI at `http://localhost:8001`
3. Open `http://localhost:8001/app/` (trailing slash required due to `basePath: '/app'`)

`pnpm dev` (port 3000) is for inner-loop development only — it is not the test path.
