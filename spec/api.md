# API

> Local single-origin JSON API (FastAPI). Same-origin as the UI at `http://localhost:8001`. Every route returns the `ok(data)` envelope or raises `api_error(code, message, status)`.

---

## API Style

REST (JSON), same-origin with the static frontend. No authentication — single local user.

## Endpoints / Commands

### `POST /datasets`
**Purpose:** Upload a CSV; load it into the local DuckDB working store; profile the schema locally; persist Dataset metadata.

**Request:** `multipart/form-data` with a `file` field (CSV).

**Response:**
```json
{ "data": { "dataset_id": "uuid", "name": "sales.csv", "row_count": 12000,
            "columns": [{"name": "region", "type": "text"}, {"name": "revenue", "type": "number"}] },
  "error": null }
```

**Error cases:**
| Status | Condition |
|--------|-----------|
| 400 | not a CSV / unparseable file (`BAD_UPLOAD`) |
| 500 | local ingestion failed (`COMPUTE_FAILED`) |

### `POST /ask`
**Purpose:** Ask a plain-English question about a dataset; run the agent; return answer + chart. Raw rows never leave the machine; only schema + aggregates reach the LLM.

**Request:**
```json
{ "dataset_id": "uuid", "question": "total revenue by region" }
```
*(Phase 2 alt: `{"connection_id": "uuid", "question": "..."}`. Phase 4 adds optional `conversation_id`.)*

**Response:**
```json
{ "data": { "question_id": "uuid", "answer_text": "The West region had the highest revenue at $410k...",
            "chart_spec": {"type": "bar", "x": "region", "series": [{"region": "West", "revenue": 410000}]},
            "status": "completed" },
  "error": null }
```

**Error cases:**
| Status | Condition |
|--------|-----------|
| 400 | unknown dataset_id / empty question (`BAD_REQUEST`) |
| 502 | Gemini unavailable (`LLM_UNAVAILABLE`) |
| 500 | local compute failed (`COMPUTE_FAILED`) |

### `POST /connections` (Phase 2)
**Purpose:** Register + validate a PostgreSQL connection string; introspect its schema locally.

**Request:** `{ "label": "prod-readonly", "connection_string": "postgresql://..." }`

**Response:** `{ "data": { "connection_id": "uuid", "label": "prod-readonly", "tables": ["orders", "customers"] }, "error": null }`

**Error cases:**
| Status | Condition |
|--------|-----------|
| 400 | malformed connection string (`BAD_REQUEST`) |
| 502 | database unreachable (`SOURCE_UNREACHABLE`) |

### `GET /questions/{id}/report` (Phase 3)
**Purpose:** Download a self-contained HTML report (answer + chart) generated locally.
**Response:** `text/html` document. Error: 404 (`NOT_FOUND`).

### `GET /health`
**Purpose:** Liveness. **Response:** `{ "data": {"status": "ok"}, "error": null }`.

## Authentication

None — single local user on `localhost`. No tokens, no accounts.
