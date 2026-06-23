# Capability: Session Management

## What It Does

Gives each browser visitor an isolated workspace via a client-generated session ID stored in localStorage, propagated as an HTTP header on every API call, and enforced server-side by table namespacing and prefix validation.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `session_id` | UUID v4 string | Browser localStorage key `analyst_session_id`, sent as `X-Session-ID` header | Yes (on every API call) |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| Session upsert acknowledgment | Implicit (no dedicated response) | `sessions` table row in SQLite; `last_seen_at` updated |
| Isolation enforcement | 403 HTTP response | When dataset_table prefix does not match session |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | UPSERT into `sessions` (INSERT OR REPLACE with last_seen_at = now()) | Return 500; do not proceed with the request |

## Business Rules

- **Session ID generation:** On first page load, the frontend generates a UUID v4 string and stores it in `localStorage` under the key `analyst_session_id`. If the key already exists, the stored value is used. The ID is never rotated within a browser session.
- **Header propagation:** Every API call (`POST /datasets/upload`, `GET /datasets`, `POST /query`, `GET /audit`) must include the `X-Session-ID` header. The server returns 422 if the header is absent or not a valid UUID format.
- **Session upsert:** On every API request bearing a valid `X-Session-ID`, the server upserts a `sessions` row: creates one if `id` is not yet known, updates `last_seen_at` if it already exists. This is a lightweight operation on every request.
- **Table namespacing:** All dynamic dataset tables are named `{session_id_underscored}_{sanitized_name}` where `session_id_underscored` is the full session UUID with hyphens replaced by underscores. This prefix ties the table irrevocably to its owning session.
- **Cross-session isolation on query:** Before invoking the LangGraph graph, `POST /query` validates that `dataset_table` starts with `{session_id_underscored}_`. A mismatch returns 403 — no SQL is executed and no audit_log row is written.
- **Dataset list isolation:** `GET /datasets` returns only `datasets` rows WHERE `session_id` = the requesting header value.
- **Audit log isolation:** `GET /audit` returns only `audit_log` rows WHERE `session_id` = the requesting header value.
- **No session expiry:** No TTL or cleanup logic is implemented in Phase 1. Sessions and their associated datasets and audit logs persist for the lifetime of the SQLite DB file.
- **No authentication:** There is no password, token, or login. Isolation is enforced purely by the naming convention and API-layer prefix check. A user who knows another session's UUID can access it — this is acceptable for a local single-user tool.
- **Footer display:** The frontend footer shows the first 8 characters of the session ID (e.g. "Session: 550e8400") so the user can confirm which session is active.

## Success Criteria

- [ ] On first page load, a UUID is generated and written to localStorage.analyst_session_id
- [ ] On subsequent page loads, the same UUID is read from localStorage — no new UUID is generated
- [ ] Every API call from the frontend includes the X-Session-ID header with the stored UUID
- [ ] POST /datasets/upload without X-Session-ID returns 422
- [ ] POST /query with a dataset_table that belongs to a different session returns 403
- [ ] GET /datasets returns only datasets belonging to the requesting session_id (not datasets from other sessions)
- [ ] GET /audit returns only audit_log rows belonging to the requesting session_id
- [ ] The sessions table has a row for every session_id that has made at least one API call
- [ ] sessions.last_seen_at is updated on every API call for that session
