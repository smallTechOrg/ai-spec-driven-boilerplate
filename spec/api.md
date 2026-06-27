# API

## API Style

REST over HTTP. JSON request/response bodies except for file upload (multipart/form-data). All responses are wrapped in `{"ok": true, "data": {...}}` on success and `{"ok": false, "error": {"code": "...", "message": "..."}}` on failure — matching the existing skeleton's `ok()` / `api_error()` helpers.

Base URL: `http://localhost:8001` (single-origin; frontend is served at `/app/`).

## Authentication

No authentication. This is a personal local tool; it binds to localhost only.

---

## Endpoints

### `GET /health`

**Purpose:** Liveness check. Existing skeleton endpoint; unchanged.

**Response:**
```json
{ "ok": true, "data": { "status": "ok" } }
```

---

### `POST /sessions`

**Purpose:** Create a new analysis session. Returns the session ID used for all subsequent file uploads and questions.

**Request:** Empty body or `{}`.

**Response (200):**
```json
{
  "ok": true,
  "data": {
    "session_id": "uuid-string",
    "created_at": "2026-06-28T12:00:00Z"
  }
}
```

**Error cases:**
| Status | Code | Condition |
|--------|------|-----------|
| 500 | `db_error` | Database write failed |

---

### `POST /sessions/{session_id}/files`

**Purpose:** Upload a CSV or Excel file. The file is parsed, ingested into a SQLite table, and its metadata stored in `uploaded_files`. The raw binary is discarded after ingest.

**Request:** `multipart/form-data` with a single field `file` containing the file binary.

**Response (200):**
```json
{
  "ok": true,
  "data": {
    "table_name": "sales_q1",
    "row_count": 1523,
    "columns": ["date", "revenue", "region"],
    "file_id": "uuid-string"
  }
}
```

**Error cases:**
| Status | Code | Condition |
|--------|------|-----------|
| 404 | `session_not_found` | `session_id` does not exist |
| 413 | `file_too_large` | File exceeds 50 MB |
| 422 | `unsupported_format` | Extension is not `.csv`, `.xlsx`, or `.xls` |
| 422 | `too_many_rows` | Parsed row count exceeds 500 000 |
| 422 | `parse_failed` | pandas could not parse the file |
| 500 | `ingest_failed` | SQLite table creation failed |

---

### `GET /sessions/{session_id}/files`

**Purpose:** List all files uploaded to a session.

**Response (200):**
```json
{
  "ok": true,
  "data": {
    "files": [
      {
        "file_id": "uuid",
        "filename": "Sales Report Q1.xlsx",
        "table_name": "sales_report_q1",
        "row_count": 1523,
        "columns": ["date", "revenue", "region"],
        "created_at": "2026-06-28T12:01:00Z"
      }
    ]
  }
}
```

**Error cases:**
| Status | Code | Condition |
|--------|------|-----------|
| 404 | `session_not_found` | `session_id` does not exist |

---

### `POST /sessions/{session_id}/analyze`

**Purpose:** Run the full analysis graph against a natural-language question. Synchronous — waits for the graph to complete before responding.

**Request:**
```json
{ "question": "What was the total revenue by region last quarter?" }
```

**Response (200):**
```json
{
  "ok": true,
  "data": {
    "run_id": "uuid",
    "status": "completed",
    "question": "What was the total revenue by region last quarter?",
    "sql_query": "SELECT region, SUM(revenue) AS total FROM sales_report_q1 GROUP BY region",
    "output_text": "Total revenue varied significantly by region...",
    "insight_json": {
      "row_count": 4,
      "numeric_columns": { "total": { "min": 12000, "max": 98000, "mean": 47500, "median": 43000, "count": 4, "null_count": 0 } },
      "top3": { "total": [98000, 76000, 54000] },
      "bottom3": { "total": [12000, 32000, 54000] },
      "anomalies": [],
      "trends": [],
      "truncated": false
    },
    "chart_specs": [
      {
        "chart_type": "bar",
        "title": "Total Revenue by Region",
        "x_axis": { "key": "region", "label": "Region" },
        "y_axes": [{ "key": "total", "label": "Total Revenue" }],
        "data": [
          { "region": "North", "total": 98000 },
          { "region": "South", "total": 32000 }
        ],
        "sampled": false
      }
    ]
  }
}
```

**Error cases:**
| Status | Code | Condition |
|--------|------|-----------|
| 404 | `session_not_found` | `session_id` does not exist |
| 422 | `no_tables` | No files have been uploaded to this session |
| 422 | `forbidden_sql_operation` | Generated SQL contains a write/DDL statement |
| 422 | `invalid_sql` | Generated SQL fails EXPLAIN QUERY PLAN validation |
| 500 | `llm_error` | Gemini API call failed |
| 500 | `execution_error` | SQL execution failed |

---

### `GET /runs/{run_id}`

**Purpose:** Get the status and result of a specific run. Existing skeleton endpoint, extended with new fields.

**Response (200):**
```json
{
  "ok": true,
  "data": {
    "run_id": "uuid",
    "status": "completed",
    "question": "...",
    "sql_query": "...",
    "output_text": "...",
    "insight_json": { ... },
    "chart_specs": [ ... ],
    "error": null,
    "created_at": "2026-06-28T12:02:00Z"
  }
}
```

**Error cases:**
| Status | Code | Condition |
|--------|------|-----------|
| 404 | `not_found` | `run_id` does not exist |
