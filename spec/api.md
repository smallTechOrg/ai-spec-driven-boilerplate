# API

---

## API Style

REST over HTTP, JSON. All success responses use the skeleton envelope `{"data": <payload>, "error": null}` via `ok(data)`. Errors raise `api_error(code, message, status)` → `{"detail": {"code", "message"}}` with the HTTP status. Served by FastAPI on port 8001; the static UI is at `/app`. Single origin → no CORS config needed.

## Endpoints / Commands

### `GET /health`

**Purpose:** Liveness. (Existing skeleton endpoint, unchanged.)
**Response:** `{"data": {"status": "ok"}, "error": null}`

### `POST /datasets`

**Purpose:** Upload a CSV/Excel file; ingest into DuckDB; create a Dataset under the active session.

**Request:** `multipart/form-data` with field `file` (the CSV/.xlsx). Optional form field `session_id` (defaults to the auto-created default session).

**Response:**
```json
{
  "data": {
    "id": "uuid",
    "name": "sales_2025",
    "session_id": "uuid",
    "row_count": 1240,
    "schema": [{"name": "region", "type": "VARCHAR"}, {"name": "amount", "type": "DOUBLE"}],
    "sample_rows": [["West", 1200.0], ["East", 980.0]]
  },
  "error": null
}
```

**Error cases:**
| Status | Condition |
|--------|-----------|
| 400 | No file / unsupported type / unparseable file / empty dataset |
| 500 | DuckDB ingestion failure |

### `GET /datasets`

**Purpose:** List datasets for the active session (newest first).
**Query:** `session_id` (optional; default session if omitted).
**Response:** `{"data": [{ id, name, row_count, schema, created_at }], "error": null}`

### `POST /ask`

**Purpose:** Ask one NL question over one dataset; run the agent; return narrative + table; write an audit row.

**Request:**
```json
{ "dataset_id": "uuid", "question": "What were total sales by region?", "session_id": "uuid (optional)" }
```

**Response:**
```json
{
  "data": {
    "run_id": "uuid",
    "narrative": "The West region led with $1.2M, followed by ...",
    "sql": "SELECT region, SUM(amount) AS total FROM dataset_ab12 GROUP BY region ORDER BY total DESC",
    "columns": ["region", "total"],
    "rows": [["West", 1200000.0], ["East", 980000.0]],
    "row_count": 4,
    "duration_ms": 37,
    "status": "completed"
  },
  "error": null
}
```
`rows` is capped to a display limit; `row_count` is the true count. (Phase 2 adds optional `chart`; Phase 3 adds optional `clarification`/`recommendations`.)

**Error cases:**
| Status | Condition |
|--------|-----------|
| 400 | Unknown `dataset_id`, empty question, or non-SELECT/invalid generated SQL |
| 502 | Gemini unavailable/rate-limited after retries (audit row `failed`) |
| 500 | DuckDB execution error (audit row `failed`) |

### `GET /audit`

**Purpose:** List audit-log entries for the session, newest first.
**Query:** `session_id` (optional), `limit` (optional, default 100).
**Response:**
```json
{
  "data": [
    {
      "id": "uuid", "dataset_id": "uuid", "nl_question": "...",
      "generated_sql": "SELECT ...", "row_count": 4, "duration_ms": 37,
      "status": "completed", "error_message": null, "created_at": "2026-06-23T..."
    }
  ],
  "error": null
}
```

### `GET /audit/export`

**Purpose:** Download the audit trail.
**Query:** `session_id` (optional), `format` = `csv` (default) | `json`.
**Response:** file download (`text/csv` or `application/json`) with the same fields as `GET /audit`.

## Authentication

None — local single-user tool on `localhost`. The only secret is `AGENT_GEMINI_API_KEY` (server-side, from `.env`, never returned by any endpoint).
