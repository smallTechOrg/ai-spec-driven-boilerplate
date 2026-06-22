# API

## API Style

REST over HTTP/1.1. JSON request/response bodies (except multipart for file upload). Served by FastAPI on `http://localhost:8000` by default.

## Authentication

No authentication in v1. Single-user local deployment. All endpoints are unauthenticated.

---

## Endpoints

### `POST /datasets`

**Purpose:** Upload a CSV or Excel file and register it as a queryable DuckDB table.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | binary | Yes | The CSV or Excel file |
| name | string | Yes | Display name for the dataset (1–100 chars) |
| description | string | No | Optional description (0–500 chars) |

**Response:** `201 Created`
```json
{
  "dataset_id": "uuid-string",
  "name": "Sales Q1 2024",
  "description": "Quarterly sales data",
  "table_name": "sales_q1_2024",
  "schema": [
    {"column": "order_id", "dtype": "int64"},
    {"column": "amount", "dtype": "float64"}
  ],
  "row_count": 4821,
  "upload_timestamp": "2026-06-23T10:00:00Z",
  "info": null
}
```

`info` is a non-null string when additional information is relevant (e.g., `"Only the first sheet was loaded from the Excel file."`).

**Error cases:**

| Status | Condition |
|--------|-----------|
| 413 | File exceeds 200 MB |
| 415 | Unsupported file type (not CSV or Excel) |
| 422 | File is unparseable (malformed CSV, corrupt Excel, no column headers) |
| 500 | Disk write failure, SQLite error, or DuckDB registration failure |

---

### `GET /datasets`

**Purpose:** List all active datasets in the catalogue.

**Request:** No body. Query params: none for v1.

**Response:** `200 OK`
```json
{
  "datasets": [
    {
      "dataset_id": "uuid-string",
      "name": "Sales Q1 2024",
      "description": "Quarterly sales data",
      "table_name": "sales_q1_2024",
      "schema": [{"column": "order_id", "dtype": "int64"}],
      "row_count": 4821,
      "upload_timestamp": "2026-06-23T10:00:00Z"
    }
  ]
}
```

Only datasets with `is_active = true` are returned. `file_path` is never included in the response.

**Error cases:**

| Status | Condition |
|--------|-----------|
| 500 | SQLite read failure |

---

### `DELETE /datasets/{dataset_id}`

**Purpose:** Soft-delete a dataset (hide from catalogue; file on disk and DuckDB registration are not removed until next restart).

**Request:** No body.

**Response:** `200 OK`
```json
{
  "dataset_id": "uuid-string",
  "is_active": false
}
```

**Error cases:**

| Status | Condition |
|--------|-----------|
| 404 | `dataset_id` not found or already inactive |
| 500 | SQLite write failure |

---

### `POST /chat`

**Purpose:** Send a user message in a session; run the agent loop; return the assistant response.

**Request:** `application/json`
```json
{
  "session_id": "uuid-string-or-null",
  "message": "What were the top 5 products by revenue last quarter?"
}
```

`session_id` is null or omitted for the first message; a new session is created and the assigned `session_id` is returned.

**Response:** `200 OK`
```json
{
  "session_id": "uuid-string",
  "response_markdown": "## Top 5 Products by Revenue\n\n| Product | Revenue |\n|---------|--------|\n...\n\n**You might also ask:**\n- ...",
  "generated_sql": "SELECT product_name, SUM(revenue) AS total ...",
  "datasets_touched": ["sales_q1_2024"],
  "row_count_returned": 5,
  "latency_ms": 3420
}
```

`generated_sql`, `datasets_touched`, and `row_count_returned` are null when Gemini returned a clarifying question (no SQL executed).

**Error cases:**

| Status | Condition |
|--------|-----------|
| 404 | `session_id` provided but not found in SQLite |
| 422 | `message` is empty or missing |
| 502 | Gemini API call failed (rate limit, invalid key, network error) |
| 500 | SQLite write failure, DuckDB error not recoverable by Gemini |

---

### `GET /sessions/{session_id}/history`

**Purpose:** Retrieve the full conversation history for a session.

**Request:** No body.

**Response:** `200 OK`
```json
{
  "session_id": "uuid-string",
  "created_at": "2026-06-23T10:00:00Z",
  "last_active": "2026-06-23T10:05:00Z",
  "turns": [
    {
      "turn_index": 1,
      "role": "user",
      "content": "What were the top 5 products?",
      "created_at": "2026-06-23T10:01:00Z",
      "is_summarised": false
    },
    {
      "turn_index": 2,
      "role": "assistant",
      "content": "## Top 5 Products...",
      "created_at": "2026-06-23T10:01:05Z",
      "is_summarised": false
    }
  ]
}
```

All turns are returned, including those with `is_summarised = true` (so the caller can see the full history). Ordered by `turn_index` ascending.

**Error cases:**

| Status | Condition |
|--------|-----------|
| 404 | `session_id` not found |
| 500 | SQLite read failure |

---

### `GET /health`

**Purpose:** Liveness check confirming the server, SQLite, and DuckDB are operational.

**Request:** No body.

**Response:** `200 OK`
```json
{
  "status": "ok",
  "sqlite": "ok",
  "duckdb": "ok",
  "registered_tables": 3
}
```

`sqlite` is `"ok"` if a simple `SELECT 1` succeeds. `duckdb` is `"ok"` if `SHOW TABLES` returns without error. If either check fails, the field is `"error"` and the HTTP status is `503`.

**Error cases:**

| Status | Condition |
|--------|-----------|
| 503 | SQLite or DuckDB health check failed |
