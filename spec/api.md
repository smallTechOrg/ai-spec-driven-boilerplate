# API

## API Style

REST. JSON request/response bodies (except the upload endpoint which is `multipart/form-data`). All successful responses are wrapped in `{"ok": true, "data": {...}}`. Errors use `{"ok": false, "error": {"code": "...", "message": "..."}}`.

Base URL (development): `http://localhost:8001`

---

## Endpoints

### `GET /health`

**Purpose:** Liveness probe. Returns `{"ok": true}` if the FastAPI process is running.

**Request:** None

**Response:**
```json
{
  "ok": true
}
```

**Error cases:** None — always returns 200 while the process is alive.

---

### `POST /sessions`

**Purpose:** Accept a CSV file upload, parse it into an in-memory pandas DataFrame, write session metadata to SQLite, and return the session context.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | binary | Yes | The CSV file. Filename used to derive a display name. |

**Response (200 OK):**
```json
{
  "ok": true,
  "data": {
    "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "columns": [
      {"name": "product_name", "dtype": "object"},
      {"name": "quantity",     "dtype": "int64"},
      {"name": "revenue",      "dtype": "float64"}
    ],
    "row_count": 1500
  }
}
```

**Fields:**
- `session_id` — UUID used in all subsequent `/sessions/{session_id}/questions` calls.
- `columns` — list of `{name, dtype}` for each column; `dtype` is the pandas dtype string.
- `row_count` — number of data rows (excluding header).

**Error cases:**

| Status | Code | Condition |
|--------|------|-----------|
| 413 | `FILE_TOO_LARGE` | File exceeds 50 MB |
| 422 | `INVALID_CSV` | File cannot be parsed as CSV or has no header row |
| 422 | `UNSUPPORTED_FORMAT` | File extension is not `.csv` |
| 422 | `TOO_MANY_COLUMNS` | File has more than 200 columns |

---

### `POST /sessions/{session_id}/questions`

**Purpose:** Run the LangGraph pipeline against an uploaded session and return the text answer (Phase 1) plus optional chart and code (Phase 2).

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | UUID string | Must match an existing session |

**Request:**
```json
{
  "question": "What is the average revenue by product category?"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `question` | string | Yes | 1–2000 characters |

**Response (200 OK — successful pipeline run):**
```json
{
  "ok": true,
  "data": {
    "run_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "status": "completed",
    "answer": "The average revenue per product category ranges from $1,200 for Electronics to $340 for Accessories. Electronics accounts for 58% of total revenue.",
    "chart_base64": null,
    "chart_type": null,
    "executed_code": null,
    "node_trace": ["parse_csv", "answer_question", "finalize"]
  }
}
```

> In Phase 2, `chart_base64` is a base64-encoded PNG string, `chart_type` is one of `"bar"` | `"line"` | `"scatter"`, and `executed_code` is the Python code string that was executed.

**Response (200 OK — pipeline failed):**
```json
{
  "ok": true,
  "data": {
    "run_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "status": "failed",
    "answer": null,
    "chart_base64": null,
    "chart_type": null,
    "executed_code": null,
    "node_trace": ["parse_csv", "handle_error"],
    "error": "Session not found. Please re-upload your CSV."
  }
}
```

> Pipeline failures return HTTP 200 with `status: "failed"` and an `error` field — not a 5xx. HTTP errors (bad request, not found) use standard 4xx codes.

**Error cases (HTTP-level):**

| Status | Code | Condition |
|--------|------|-----------|
| 404 | `SESSION_NOT_FOUND` | `session_id` not found in session metadata |
| 422 | `VALIDATION_ERROR` | `question` is empty or exceeds 2000 characters |
| 422 | `VALIDATION_ERROR` | `session_id` is not a valid UUID |

---

### `GET /runs/{run_id}`

**Purpose:** Retrieve the stored result of a previously completed run (observability / history).

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | UUID string | Must match an existing `ConversationRun` record |

**Response (200 OK):**
```json
{
  "ok": true,
  "data": {
    "run_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "question": "What is the average revenue by product category?",
    "answer": "The average revenue...",
    "status": "completed",
    "chart_base64": null,
    "chart_type": null,
    "executed_code": null,
    "created_at": "2026-06-27T10:00:00Z"
  }
}
```

**Error cases:**

| Status | Code | Condition |
|--------|------|-----------|
| 404 | `RUN_NOT_FOUND` | `run_id` not found in `conversation_runs` |

---

## Authentication

None. All endpoints are open. Authentication is explicitly out of scope.

---

## Shared Response Envelope

All successful responses:
```json
{"ok": true, "data": {...}}
```

All error responses:
```json
{"ok": false, "error": {"code": "SNAKE_CASE_CODE", "message": "Human-readable message."}}
```

The `api/_common.py` helpers `ok(data)` and `api_error(code, message, status)` implement this envelope.
