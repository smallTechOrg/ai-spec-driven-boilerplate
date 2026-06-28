# API — DataChat

---

## API Style

**REST (JSON)** over HTTP on a single origin (`http://localhost:8001`), plus **SSE** for streaming in P4. Served by FastAPI; the Next.js UI calls these same-origin from `/app/`. Every JSON response uses the skeleton envelope `{"data": ..., "error": null}` (`src/api/_common.ok`); errors are `{"detail": {"code", "message"}}` with an HTTP status. No auth (single local user).

Phase tags mark when each endpoint is introduced.

## Endpoints

### `POST /datasets`  *(P1)*
Upload + auto-profile a spreadsheet. `multipart/form-data` with `file` (CSV/Excel, up to ~100MB) and optional `name`. Saves the file locally, profiles it (no rows to the LLM), persists `Dataset` + `DatasetProfile`.
- **200:** `{ dataset: {id, name, kind, row_count, column_count, size_bytes, created_at}, profile: {columns:[{name,dtype,non_null,n_unique,min,max,sample_values}], row_count, quality_flags?} }`
- **400:** unsupported file type / unreadable / too large.

### `GET /datasets/{id}`  *(P1)*
Fetch a dataset + its latest profile. **200:** same shape as upload's body. **404** if unknown.

### `GET /datasets`  *(P2)*
List the library (most-recent first). **200:** `{ datasets: [{id, name, kind, row_count, column_count, created_at}] }`.

### `DELETE /datasets/{id}`  *(P2)*
Remove a dataset (row + file + dependent conversations/runs). **200:** `{deleted: id}`.

### `POST /datasets/{id}/ask`  *(P1)*
Ask one question against a dataset (P1 single-shot; P2 prefers the conversation endpoint). Body `{question}`. Runs the graph; persists an `AnalysisRun`.
- **200:** `{ run: {id, question, answer, code, result_summary, tokens:{prompt,completion,total}, cost_usd, status, assumptions?, followups?, viz?, steps?:[{step_index,phase,code,error}], created_at, completed_at} }`
- **404** unknown dataset; **200 with status="failed"** + `error_message` when the agent could not compute (honest failure, not a 500).

### `POST /conversations`  *(P2)*
Start a thread. Body `{dataset_id, title?}`. **200:** `{conversation: {id, dataset_id, title, created_at}}`.

### `GET /conversations`  *(P2)*
List threads (most-recent first). **200:** `{conversations:[{id, dataset_id, title, updated_at}]}`.

### `GET /conversations/{id}`  *(P2)*
Thread + its messages. **200:** `{conversation:{...}, messages:[{id, role, content, run_id?, created_at}]}`.

### `GET /conversations/{id}/messages`  *(P2)*
Just the messages (pagination-friendly). **200:** `{messages:[...]}`.

### `POST /conversations/{id}/ask`  *(P2)*
Ask within a thread; prior turns are threaded as memory (summaries only, never rows). Body `{question}`. Same `run` shape as `/datasets/{id}/ask`, and appends a `user` + `assistant` `Message`.

### `GET /conversations/{id}/ask/stream`  *(P4 — SSE)*
Streaming variant. Query `?question=`. Emits SSE events:
- `event: step` → `{step_index, phase, code?}` (timeline updates: planning → running_code → checking_result)
- `event: token` → `{text}` (answer tokens)
- `event: done` → the full `run` object (incl. `viz`, `followups`, tokens, cost)
- `event: error` → `{code, message}`

### `GET /runs/{id}`  *(P1)*
Fetch one run (the persisted record incl. code, result, tokens, cost, steps). **200:** `{run: {...}}`. **404** if unknown.

### `GET /runs`  *(P2 list; P4 browser)*
Run history. Query `?conversation_id=` (P2) or all (P4), most-recent first. **200:** `{runs:[{id, dataset_id, question, answer, code, total_tokens, cost_usd, status, created_at}]}`.

### `GET /usage/daily`  *(P4)*
Daily cost rollup. **200:** `{today: {date, total_cost_usd, run_count}, days:[{date, total_cost_usd, run_count}]}`.

### `GET /health`  *(skeleton, retained)*
Liveness. **200:** `{status:"ok"}`.

## Privacy Contract (applies to every endpoint)

No endpoint returns raw data rows except as the **bounded, user-requested computed result** of their own question (e.g. a small head/aggregate the generated code produced). No endpoint sends raw rows to Gemini — the LLM-facing payload is always question + profile + result summaries. Asserted in `tests/test_phase1_privacy.py` by inspecting the outbound prompt.

## Streaming Note

Streaming is **deferred to P4**. P1–P3 answers return synchronously from `*/ask`. The SSE endpoint is a new surface in P4, not a change to the synchronous ones (which remain for non-streaming clients/tests).
