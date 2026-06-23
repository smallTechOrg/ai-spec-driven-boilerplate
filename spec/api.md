# API

## API Style

REST. All responses are plain `application/json`. No SSE streaming, no envelope wrapper — raw JSON objects as documented below.

Base URL: `http://localhost:8001` (dev). Frontend calls these from the same origin (no CORS needed in production single-origin mode).

## Authentication

None. Session identity is carried by the `X-Session-ID` request header (a UUID generated client-side and stored in `localStorage`). Every mutating or data-reading endpoint requires this header.

---

## Endpoints

### `GET /health`

**Purpose:** Liveness check.

**Request:** No headers or body required.

**Response `200`:**
```json
{"status": "ok", "version": "0.1.0"}
```

---

### `POST /datasets/upload`

**Purpose:** Upload a CSV or Excel file and ingest it into a session-namespaced SQLite table.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Header: `X-Session-ID: <uuid>` (required)
- Form field: `file` — the file to upload (`.csv` or `.xlsx`)

**Validation rules:**
- `X-Session-ID` header must be present and a valid UUID format — 422 if missing or malformed
- File extension must be `.csv` or `.xlsx` — 422 if unsupported type
- File must parse without error — 422 if pandas raises on read
- File must not be empty (zero rows after header) — 422 if empty
- File must not exceed 500,000 rows — 422 if over limit (checked after parsing, before ingestion)

**Response `200`:**
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "table_name": "550e8400_e29b_41d4_a716_446655440000_sales_report",
  "original_filename": "sales report.xlsx",
  "row_count": 1234,
  "column_names": ["date", "region", "revenue"],
  "created_at": "2026-06-23T10:05:00Z"
}
```

**Error responses:**
| Status | Condition |
|--------|-----------|
| 422 | Missing X-Session-ID; unsupported file type; parse error; empty file; over 500k rows |
| 500 | SQLite write failure |

**Side-effects:**
1. Upserts a `sessions` row for the given session_id (creates if not exists, updates `last_seen_at`).
2. Calls `DataFrame.to_sql(table_name, engine, if_exists="replace", index=False)`.
3. Inserts a `datasets` row.

---

### `GET /datasets`

**Purpose:** List all datasets uploaded in this session.

**Request:**
- Method: `GET`
- Header: `X-Session-ID: <uuid>` (required)

**Validation rules:**
- `X-Session-ID` must be present and a valid UUID format — 422 if missing or malformed

**Response `200`:**
```json
[
  {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "table_name": "550e8400_e29b_41d4_a716_446655440000_sales_report",
    "original_filename": "sales report.xlsx",
    "row_count": 1234,
    "column_names": ["date", "region", "revenue"],
    "created_at": "2026-06-23T10:05:00Z"
  }
]
```

Returns an empty array `[]` if the session has no datasets (not 404). Updates `sessions.last_seen_at`.

---

### `POST /query`

**Purpose:** Ask a natural-language question about a specific dataset. Runs the LangGraph analyst graph and returns the answer.

**Request:**
- Method: `POST`
- Content-Type: `application/json`
- Header: `X-Session-ID: <uuid>` (required)
- Body:
```json
{
  "question": "What are the top 5 regions by revenue?",
  "dataset_table": "550e8400_e29b_41d4_a716_446655440000_sales_report"
}
```

**Validation rules:**
- `X-Session-ID` must be present and a valid UUID format — 422 if missing or malformed
- `question` must be a non-empty string — 422 if blank or missing
- `dataset_table` must be a non-empty string — 422 if blank or missing
- `dataset_table` must start with `{session_id_underscored}_` (where `session_id_underscored` is the X-Session-ID with hyphens replaced by underscores) — 403 if prefix does not match (cross-session access attempt)
- `dataset_table` must exist in SQLite (verified via `SELECT 1 FROM datasets WHERE table_name = ? AND session_id = ?`) — 404 if not found

**Response `200` (success):**
```json
{
  "answer": "The top 5 regions by revenue are North America ($2.3M), EMEA ($1.8M), APAC ($900K), LATAM ($450K), and MEA ($200K).\n\nReturned 5 row(s).",
  "table": [
    {"region": "North America", "revenue": 2300000},
    {"region": "EMEA", "revenue": 1800000}
  ],
  "sql": "SELECT region, SUM(revenue) AS revenue FROM 550e8400_e29b_41d4_a716_446655440000_sales_report GROUP BY region ORDER BY revenue DESC LIMIT 5",
  "audit_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Response `502` (graph error — Gemini failure, SQL execution failure, etc.):**
```json
{
  "error": "Gemini API error after 3 retries: quota exceeded"
}
```

**HTTP status codes:**
| Status | Condition |
|--------|-----------|
| 200 | Graph completed successfully |
| 403 | dataset_table prefix does not match session_id |
| 404 | dataset_table not found in this session's datasets |
| 422 | Missing or invalid X-Session-ID, question, or dataset_table |
| 502 | Graph set state["error"] — Gemini failure, SQL execution failure, etc. |

**Side-effects:**
- Upserts `sessions.last_seen_at`.
- `audit_logger` node writes one `audit_log` row (even on 502 — the row records the error).

---

### `GET /audit`

**Purpose:** Retrieve the audit log for this session, newest first.

**Request:**
- Method: `GET`
- Header: `X-Session-ID: <uuid>` (required)

**Validation rules:**
- `X-Session-ID` must be present and a valid UUID format — 422 if missing or malformed

**Response `200`:**
```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "dataset_table": "550e8400_e29b_41d4_a716_446655440000_sales_report",
    "question": "What are the top 5 regions by revenue?",
    "sql_generated": "SELECT region, SUM(revenue) AS revenue FROM ... LIMIT 5",
    "row_count": 5,
    "duration_ms": 42,
    "error": null,
    "created_at": "2026-06-23T10:06:04Z"
  }
]
```

Returns an empty array `[]` if no audit entries exist for this session. Updates `sessions.last_seen_at`. Ordered by `created_at DESC`.
