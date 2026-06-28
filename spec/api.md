# API

REST API for the Local Data Analyst. All responses use the existing envelope: success → `{"data": <payload>, "error": null}` (via `ok(data)`); failure → HTTP error with `{"detail": {"code", "message"}}` (via `api_error(code, message, status)`). This file is the **contract the frontend slice builds to in parallel** — the field names and shapes below are binding.

---

## API Style

REST (JSON), served by FastAPI on port 8001. The Next.js static UI at `/app/` calls these endpoints. No authentication (single-user, local-only). Routers live in `src/api/` and are registered in `src/api/__init__.py`.

> **Assumed:** all data endpoints are namespaced under `/api/` (e.g. `/api/datasets`, `/api/ask`) to avoid colliding with the `/app/` static mount and the existing `/health`. The skeleton's `/runs` router is replaced by `/api/runs`.

## Endpoints / Commands

### `POST /api/datasets` — Phase 1 (REAL)

**Purpose:** Upload one CSV or Excel file, load it into DuckDB, auto-profile it, and create a library entry. Each Excel sheet becomes its own dataset (the endpoint returns one entry per sheet for Excel; one for CSV).

**Request:** `multipart/form-data` with a single `file` field (CSV or `.xlsx`, up to ~100 MB).

**Response:**
```json
{
  "data": {
    "datasets": [
      {
        "id": "uuid",
        "name": "sample_sales.csv",
        "source_kind": "csv",
        "sheet_name": null,
        "row_count": 5000,
        "profile": {
          "row_count": 5000,
          "columns": [
            {"name": "region", "type": "VARCHAR", "null_count": 0},
            {"name": "amount", "type": "DOUBLE", "null_count": 3,
             "min": 0.0, "max": 9999.0, "mean": 412.5}
          ]
        }
      }
    ]
  },
  "error": null
}
```

**Error cases:**
| Status | Condition |
|--------|-----------|
| 400 | Unsupported file type, empty file, or unparseable CSV/Excel |
| 413 | File exceeds the configured max size |
| 500 | DuckDB load or profiling failure |

### `POST /api/ask` — Phase 1 (REAL)

**Purpose:** Ask a plain-English question of a loaded dataset; run the PLAN-THEN-EXECUTE graph; return the rich-answer envelope. Persists a Run audit record.

**Request:**
```json
{
  "dataset_id": "uuid",
  "question": "What were total sales by region?"
}
```

**Response:**
```json
{
  "data": {
    "run_id": "uuid",
    "status": "completed",
    "answer": "Total sales were highest in the West region at $1.2M…",
    "key_stats": [
      {"label": "Top region", "value": "West"},
      {"label": "Total sales", "value": 1200000, "unit": "USD"}
    ],
    "chart_spec": {
      "type": "bar",
      "x": "region",
      "y": "total_sales",
      "data": [{"region": "West", "total_sales": 1200000}]
    },
    "summary_table": {
      "columns": ["region", "total_sales"],
      "rows": [["West", 1200000], ["East", 900000]]
    },
    "insight": "Sales are concentrated in the West, which is 33% above the next region…",
    "follow_ups": [
      "How did West sales trend month over month?",
      "Which products drove West's lead?"
    ],
    "plan_steps": [
      "Group rows by region",
      "Sum the amount column per region",
      "Order regions by total descending"
    ],
    "generated_sql": "SELECT region, SUM(amount) AS total_sales FROM ds GROUP BY region ORDER BY total_sales DESC",
    "cost": {
      "prompt_tokens": 812,
      "completion_tokens": 240,
      "est_usd": 0.00042
    }
  },
  "error": null
}
```

On a failed run the response is HTTP 200 with `status: "failed"`, the `answer`/`insight` empty, `generated_sql` showing what was attempted, and an `error` message inside `data` so the UI shows what was tried. (Transport-level failures use `api_error`.)

**Error cases:**
| Status | Condition |
|--------|-----------|
| 400 | Missing `dataset_id` or `question` |
| 404 | `dataset_id` not found |
| 200 (status="failed") | Graph error (bad SQL, Gemini failure) — surfaced transparently with attempted SQL |

> **Privacy note:** the request carries only the dataset_id + question. No raw rows are accepted or returned beyond the capped `summary_table` (aggregates). Raw rows are never in this contract.

### `GET /api/runs` — Phase 1 (REAL)

**Purpose:** List the audit history (most recent first), for the history panel and (Phase 5) re-run.

**Response:**
```json
{
  "data": {
    "runs": [
      {
        "id": "uuid",
        "dataset_id": "uuid",
        "status": "completed",
        "question": "What were total sales by region?",
        "generated_sql": "SELECT …",
        "est_usd": 0.00042,
        "created_at": "2026-06-28T10:00:00Z"
      }
    ]
  },
  "error": null
}
```

### `GET /api/runs/{run_id}` — Phase 1 (REAL)

**Purpose:** Fetch one full Run audit record (question, plan, SQL, result summary, tokens, cost) for inspection.

**Response:** `ok(<full run record, same shape as the /api/ask data minus follow_ups, including plan_json, result_summary_json, prompt_tokens, completion_tokens, est_usd, timestamps>)`.

**Error cases:**
| Status | Condition |
|--------|-----------|
| 404 | Run not found |

### `GET /health` — existing (REAL)

Unchanged skeleton endpoint: `ok({"status": "ok"})`.

---

### Stubbed-for-later endpoints (NOT in Phase 1)

These are documented so the frontend stubs link to the right contract; they are **not implemented in Phase 1**.

| Endpoint | Phase | Purpose |
|----------|-------|---------|
| `GET /api/datasets`, `DELETE /api/datasets/{id}` | 2 | List / delete library datasets |
| `GET /api/session`, `POST /api/session` | 2 | Restore / update the active session + history |
| `GET /api/datasets/{id}/messages` | 2 | Conversation history for a dataset |
| `POST /api/ask` with `dataset_ids: [...]` | 3 | Multi-file join / folder-as-dataset ask |
| `POST /api/datasets/folder` | 3 | Folder-as-dataset ingestion |
| `POST /api/ask/clarify` | 4 | Clarification round-trip |
| `POST /api/watch` | 4 | Configure the watched folder |
| `GET /api/cost/daily` | 5 | Daily cost rollup |
| `POST /api/datasets/{id}/derive`, `POST /api/runs/{id}/rerun` | 5 | Save derived table / reproducible re-run |

## Authentication

None. Single-user, local-only service bound to localhost. No API keys, tokens, or sessions for callers.
