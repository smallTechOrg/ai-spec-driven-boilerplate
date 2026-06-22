# API

REST over FastAPI, port **8001**. All responses use the existing envelope from `src/api/_common.py` (`ok(...)` / `api_error(...)`). Existing `GET /health` retained.

## Datasets

### `POST /datasets`
Upload a CSV and register it as a queryable dataset.
- **Body:** `multipart/form-data`, field `file` (CSV; Excel in Phase 5).
- **Action:** ingest into DuckDB table `ds_<id>`, capture schema, write `Dataset` + `AuditLog(operation=ingest)`.
- **200:** `{ id, name, row_count, schema: [{name, type}] }`
- **Errors:** `BAD_REQUEST` (unparseable/empty file), unsupported type.

### `GET /datasets`
List registered datasets.
- **200:** `{ datasets: [{ id, name, row_count, created_at }] }`

## Sessions

### `POST /sessions`
Create a session.
- **200:** `{ id, title, created_at }`

### `GET /sessions`
List sessions (most recent first).
- **200:** `{ sessions: [{ id, title, updated_at }] }`

### `GET /sessions/{id}/messages`
Full message history for a session (persistence on reload).
- **200:** `{ messages: [{ id, role, content, sql, result, dataset_id, created_at }] }` where `result` = `{columns, rows}` or null.

### `POST /sessions/{id}/query`
Ask a natural-language question against a dataset.
- **Body:** `{ dataset_id: str, question: str }`
- **Action:** persist user `Message`, invoke the agent graph, persist assistant `Message`.
- **200:** `{ message_id, answer, sql, result: { columns, rows }, row_count }`
- **Errors:** `NOT_FOUND` (session/dataset), `QUERY_FAILED` (SQL generation/execution failed — `error` surfaced from `handle_error`).

## Notes

- Charts (Phase 2), audit read endpoint (Phase 5), cross-dataset list selection (Phase 3) extend this contract; not present in Phase 1.
- The frontend slice codes against this contract independently of the backend slice.
