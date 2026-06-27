# UI

## UI Type

Web single-page application at `/app/` — Next.js 15 static export served by FastAPI. The user opens one URL and never navigates away.

## Layout

Single page, top to bottom:
1. Header
2. Data Source Panel
3. File Upload Area (conditional)
4. Chat Input (conditional)
5. Results Area

## Sections

### 1. Header

Title: "Data Analysis Agent"
Subtitle: "Upload a file and ask questions about your data."

---

### 2. Data Source Panel

Two options displayed side by side:

- **"Upload File"** — primary style (filled/solid button), active by default, highlights to show it is selected
- **"Connect Database (Phase 2)"** — secondary/outline style, always clickable, opens the Phase 2 modal on click

The active tab controls which content appears below the panel.

---

### 3. File Upload Area (shown when "Upload File" is selected)

States:

**Empty (default):**
- Dashed-border dropzone
- Centered text: "Drop your CSV or Excel file here, or click to browse"
- Accepts .csv, .xlsx, .xls

**Uploading:**
- Shows filename
- Shows spinner with "Uploading..."

**Uploaded (success):**
- Shows filename
- Shows column list: "Columns: month, product, revenue"
- Shows row count: "150 rows"
- Shows a "Change file" link to reset and upload a new file

**Error:**
- Red border
- Error message text (e.g. "Only CSV and Excel files are accepted.")

---

### 4. Chat Input (shown after a file is successfully uploaded)

- Textarea with placeholder: "Ask a question about your data…"
- "Analyze" button (primary, disabled while a request is in-flight)
- Example questions shown as small muted text below the textarea:
  - "Show revenue by month"
  - "Compare sales by product"
  - "Plot trends over time"

---

### 5. Results Area

Empty state (before any analysis): centered placeholder text "Upload a file and ask a question to see results."

After analysis (newest result at top):

Each result is a ResultCard containing:
- **QuestionLabel** — the question text the user submitted
- **ChartPanel** — Recharts chart matching chart_type:
  - `"bar"` → BarChart
  - `"line"` → LineChart
  - `"scatter"` → ScatterChart
  - All charts: ResponsiveContainer width="100%" height={350}, CartesianGrid, XAxis (labels), YAxis (values), Tooltip with exact values
- **SummaryCard** — white rounded card, plain text summary paragraph

Loading state (while /analyze is in-flight):
- Spinner or skeleton in the ResultCard position
- Analyze button disabled

Error state (if /analyze returns error):
- Error message shown in a red-bordered card where the ResultCard would be

---

### 6. Phase 2 Modal

Triggered by clicking "Connect Database (Phase 2)" button.

- Overlay (semi-transparent dark backdrop)
- White centered modal card
- Message: "PostgreSQL database connection is coming in Phase 2. Stay tuned!"
- Close button (top-right X or "Got it" button at bottom)
- Clicking outside the modal also closes it

---

## Component Tree

```
page.tsx
├── Header
├── DataSourcePanel
│   ├── UploadFileTab (primary, active in Phase 1)
│   └── ConnectDatabaseButton (secondary/outline, Phase 2 stub)
├── FileUploadDropzone (shown when UploadFileTab selected)
│   └── states: empty | uploading | uploaded | error
├── ChatInput (shown after file uploaded)
│   ├── Textarea
│   ├── AnalyzeButton (disabled while loading)
│   └── ExampleQuestions
├── ResultsArea
│   ├── EmptyPlaceholder (before first analysis)
│   └── ResultCard (per response, newest first)
│       ├── QuestionLabel
│       ├── ChartPanel (Recharts BarChart / LineChart / ScatterChart)
│       └── SummaryCard
└── DatabaseModal (Phase 2 stub modal, conditionally rendered)
```

## Stubs (Phase 1)

| Surface | Status | User-facing label |
|---------|--------|-------------------|
| "Connect Database (Phase 2)" button | Non-functional stub | Button label reads "(Phase 2)" |
| Phase 2 Modal | Informational only | Shows "coming in Phase 2" message |
| ResultsArea | Real on the tested path | Starts empty; fills after analysis |

No stub is hidden or broken-looking. Every stub shows clear labelling so the user understands it is intentionally deferred.

## Error States

| Situation | UI Response |
|-----------|-------------|
| Wrong file type uploaded | Red border on dropzone + "Only CSV and Excel files are accepted." |
| Upload fails (server error) | Red border on dropzone + error message text |
| Analysis fails (server error) | Red-bordered error card in ResultsArea with message |
| Network unreachable | Generic error card: "Unable to reach the server. Please check the app is running." |
