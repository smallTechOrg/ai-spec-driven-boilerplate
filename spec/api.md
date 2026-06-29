# API

## API Style

REST. JSON envelope: `{"data": <payload>, "error": null}` on success; `{"data": null, "error": {"code": "...", "message": "..."}}` on error. All routes return HTTP 200 even for application errors (except 404/422).

---

## Endpoints

### POST /sessions

Create a new analysis session.

**Request:** no body

**Response 200:**
```json
{
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2026-06-29T12:00:00Z"
  },
  "error": null
}
```

---

### POST /sessions/{session_id}/files

Upload a CSV file. Saves to temp dir, runs profiling (no LLM), returns profile. Multipart form upload.

**Request:** `multipart/form-data` with field `file` (CSV file, content-type text/csv or application/octet-stream)

**Response 200:**
```json
{
  "data": {
    "file_id": "uuid-string",
    "filename": "sales.csv",
    "profile": {
      "row_count": 1250,
      "column_count": 8,
      "columns": [
        {
          "name": "revenue",
          "dtype": "float64",
          "null_count": 3,
          "null_pct": 0.24,
          "stats": {"min": 0.0, "max": 99999.9, "mean": 5432.1, "std": 3210.5, "p25": 1200.0, "p50": 4500.0, "p75": 8900.0},
          "sample_values": ["1200.0", "8450.5", "320.0"]
        },
        {
          "name": "region",
          "dtype": "object",
          "null_count": 0,
          "null_pct": 0.0,
          "value_counts": {"West": 420, "East": 380, "North": 250, "South": 200},
          "sample_values": ["West", "East", "North"]
        }
      ],
      "quality_flags": [
        {"type": "WARNING", "column": "revenue", "message": "3 null values (0.24%)"},
        {"type": "WARNING", "column": null, "message": "42 duplicate rows detected"}
      ]
    }
  },
  "error": null
}
```

**Error 400:** `{"data": null, "error": {"code": "INVALID_FILE", "message": "Only CSV files are supported in Phase 1"}}`
**Error 404:** `{"data": null, "error": {"code": "SESSION_NOT_FOUND", "message": "Session not found"}}`

---

### POST /sessions/{session_id}/messages

Send a natural-language question. Runs Q&A pipeline (LangGraph). Returns assistant response.

**Request:**
```json
{"content": "Show me a bar chart of revenue by region"}
```

**Response 200:**
```json
{
  "data": {
    "message_id": "uuid-string",
    "role": "assistant",
    "content": "Revenue by region shows the West leading at $2.1M, followed by East at $1.8M, North at $1.1M, and South at $0.9M.",
    "chart_json": {
      "data": [{"type": "bar", "x": ["West", "East", "North", "South"], "y": [2100000, 1800000, 1100000, 900000]}],
      "layout": {"title": "Revenue by Region"}
    }
  },
  "error": null
}
```

`chart_json` is `null` when no chart was generated.

**Error 400:** `{"data": null, "error": {"code": "NO_FILES", "message": "Upload a CSV file before asking questions"}}`
**Error 404:** Session not found.

---

### GET /sessions/{session_id}/messages

Get full conversation history for the session.

**Response 200:**
```json
{
  "data": {
    "messages": [
      {
        "message_id": "uuid-1",
        "role": "user",
        "content": "Show me revenue by region",
        "chart_json": null,
        "created_at": "2026-06-29T12:01:00Z"
      },
      {
        "message_id": "uuid-2",
        "role": "assistant",
        "content": "Revenue by region shows the West leading...",
        "chart_json": {"data": [...], "layout": {...}},
        "created_at": "2026-06-29T12:01:05Z"
      }
    ]
  },
  "error": null
}
```

---

### DELETE /sessions/{session_id}

Delete session, all messages, and all uploaded temp files from disk.

**Response 200:**
```json
{"data": {"deleted": true}, "error": null}
```

---

### GET /health

Health check.

**Response 200:**
```json
{"data": {"status": "ok"}, "error": null}
```

---

## Authentication

No authentication in Phase 1. Session IDs are UUID v4 (unguessable). All data is ephemeral.

---

## Static Frontend

`GET /app/*` serves the Next.js static export (frontend/out/) via FastAPI StaticFiles. Returns 404 if frontend not built. Frontend is built with `cd frontend && pnpm build` before starting the server.
