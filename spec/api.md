# API

Single-origin FastAPI. All JSON responses use the baseline envelope `{ "data": ..., "error":
null }`; errors are `HTTPException` with `detail = {code, message}`. The frontend static export
is served at `/app`. Backend listens on port **8001** (`uv run python -m src`).

## `GET /health`
Liveness. → `200 {"data": {"status": "ok"}, "error": null}`. (Existing.)

## `POST /datasets`
Upload one tabular file. **Multipart form** with field `file`.

- **Phase 1:** accepts `.csv` only. **Phase 3:** also `.xlsx`.
- Validates size (≤ `max_upload_mb`) and that it parses; rejects otherwise.
- Saves to `data/uploads/<id>.<ext>`; derives + persists schema + bounded sample.

Response `200`:
```json
{ "data": {
    "dataset_id": "…uuid…",
    "filename": "sales.csv",
    "row_count": 1234,
    "schema": [{"name": "region", "dtype": "object"}, {"name": "amount", "dtype": "float64"}],
    "sample_preview": [ { "region": "West", "amount": 100.0 } ]
  }, "error": null }
```
Errors: `400 BAD_FILE` (not parseable / wrong type), `413 TOO_LARGE`.

## `POST /datasets/{dataset_id}/ask`
Ask one natural-language question about an uploaded dataset. Runs the agent graph synchronously
and returns the audited answer.

Request body:
```json
{ "question": "Which region has the highest average amount?",
  "conversation_id": "" }   // Phase 2: set to dataset_id to chat across turns; ignored in P1
```

Response `200` (the three guarantees + audit fields):
```json
{ "data": {
    "query_id": "…uuid…",
    "dataset_id": "…uuid…",
    "status": "completed",
    "answer": "West, with an average amount of 142.50",
    "explanation": "Grouping rows by region and averaging the amount column, West is highest…",
    "code": "result = df.groupby('region')['amount'].mean().idxmax()",
    "result": "West",
    "model": "gemini-2.5-flash",
    "tokens_in": 812, "tokens_out": 64, "cost_usd": 0.0003, "latency_ms": 1840
  }, "error": null }
```

Failure `200` with `status: "failed"` (graceful, human-readable — never a stack trace):
```json
{ "data": { "query_id": "…", "status": "failed",
    "error": "Could not compute an answer for this question.", "code": null },
  "error": null }
```
Hard errors: `404 NOT_FOUND` (unknown dataset_id), `400 BAD_REQUEST` (empty question).

> **Phase 4** adds an optional `"chart": {"type": "bar", "x": [...], "y": [...]}` object to the
> `/ask` response when the question is chartable (aggregated series only — no raw data egress).

> The baseline `/runs` endpoints are superseded by `/datasets` + `/ask` and are not part of the
> analysis surface.
