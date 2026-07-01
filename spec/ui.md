# UI

## Layout

Single-page application at `http://localhost:8001/app/`. Next.js 15 static export + Tailwind v4 + TypeScript.

Two-panel layout:
- **Left panel (30% width):** File upload zone + profile summary cards
- **Right panel (70% width):** Chat interface with message history + input at bottom

---

## Components

### FileUpload (left panel, top)
- Drag-and-drop zone or click-to-select for CSV files
- Subtext: "CSV only — Excel support coming in Phase 2"
- On upload: show spinner + "Profiling your data..."
- On success: hide dropzone, show ProfileCard
- Phase 2 stub below profile card: disabled button "Upload another file [Coming in Phase 2]"

### ProfileCard (left panel, below upload area)
- Card header: filename (bold) + "N rows · M columns" subtext
- Column list: each column as a row with:
  - Name
  - Dtype chip (blue=numeric, green=text/object, yellow=datetime, grey=other)
  - Null % as a small inline progress bar
  - Sample values as grey chips (first 3)
- Quality flags section: yellow badge for WARNINGs, red badge for ERRORs
- Footer: disabled grey button "Export Data [Coming in Phase 2]"

### ChatMessage (right panel, message list)
- User messages: right-aligned, blue background bubble
- Assistant messages: left-aligned, white card with border
- Assistant messages may include a PlotlyChart component below the text
- Loading state: assistant placeholder with animated pulse while waiting

### PlotlyChart (inside assistant ChatMessage)
- Renders Plotly JSON spec using react-plotly.js (dynamic import to avoid SSR issues)
- Full width of message card, height 350px
- Interactive: zoom, pan, hover tooltips enabled
- Renders nothing when chart_json is null

### ChatInput (right panel, fixed bottom)
- Multi-line textarea, max 3 rows
- Send button (right side, primary color)
- Disabled while response is loading
- Shows "Analyzing your data..." below input while loading
- Optimistic UI: user message appears immediately in chat on submit

---

## Interaction Flow

1. Page loads → left panel shows upload dropzone; right panel shows "Upload a CSV file to get started"
2. User selects CSV → spinner in left panel "Profiling your data..."
3. Profile card appears with file summary + quality flags
4. User types question in chat input → clicks Send
5. User message appears immediately (right-aligned, blue)
6. "Analyzing your data..." shown below input; loading placeholder in chat
7. Response arrives: text + optional interactive Plotly chart in assistant bubble
8. User types follow-up; repeat from step 4
9. Chat scrolls to latest message automatically

---

## Phase 1 Stubs (clearly labelled, never look like bugs)

| Stub | Location | Label |
|------|----------|-------|
| Multi-file upload | Below profile card | Disabled button: "Upload another file [Coming in Phase 2]" |
| Export data | Profile card footer | Disabled button: "Export Data [Coming in Phase 2]" |
| Excel support | Upload dropzone subtext | "CSV only — Excel support coming in Phase 2" |
| File comparison | Right panel empty state hint | "Compare files across sessions — Phase 2" |

---

## Error States

- Upload fails: red border on dropzone + error message below
- Q&A error: assistant message in red-tinted card with error text from API
- Network error: inline error in chat "Connection error — please try again"

---

## Technical Notes

- API base URL: `http://localhost:8001` (hardcoded for Phase 1; configurable via NEXT_PUBLIC_API_URL for Phase 2)
- Session ID stored in React state (not localStorage — session-only, lost on page refresh is acceptable)
- react-plotly.js for chart rendering, dynamic import to avoid Next.js static export SSR issues
- Tailwind v4 with `@source` directive for static export compatibility
- `next.config.ts` must have `output: "export"` and `basePath: "/app"` (or trailingSlash: true)
