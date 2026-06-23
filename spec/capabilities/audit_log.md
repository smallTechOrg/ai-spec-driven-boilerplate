# Capability: Audit Log

## What It Does

Records every POST /query call as an immutable audit_log row in SQLite, capturing the session, dataset, question, generated SQL, result metrics, and any error — then exposes these records through the GET /audit endpoint.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `session_id` | UUID string | AnalystState | Yes |
| `dataset_table` | string | AnalystState | Yes |
| `question` | string | AnalystState | Yes |
| `sql` | string (the generated SQL) | AnalystState (from query_planner) | No — null if query_planner failed |
| `row_count` | int | AnalystState (from sql_executor) | No — null if sql_executor did not run |
| `duration_ms` | int | AnalystState (from sql_executor) | No — null if sql_executor did not run |
| `error` | string | AnalystState | No — null on success |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `audit_id` | UUID string | AnalystState → POST /query response body |
| Audit log list | Array of audit_log objects | GET /audit response body |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | INSERT into `audit_log` table | Log warning via structlog at WARNING level; do not set state["error"]; do not fail the query response |
| SQLite | SELECT from `audit_log` WHERE session_id = ? ORDER BY created_at DESC | Return 500 from GET /audit endpoint |

## Business Rules

- **Always writes:** One `audit_log` row is written for every `POST /query` call, including calls that return 502 (graph errors). The row captures whatever state was available at the time of the `audit_logger` node execution.
- **Fields on error:** When the graph errors in `query_planner`, `sql_generated` is null. When it errors before or during `sql_executor`, `row_count` and `duration_ms` are null. The `error` field captures the error message string.
- **Fields on success:** `sql_generated`, `row_count`, and `duration_ms` are all populated. `error` is null.
- **Non-fatal writes:** An INSERT failure (e.g. SQLite locked) is logged via structlog at WARNING level but does not propagate. The query response is returned to the client regardless. `audit_id` will be absent from the response if the INSERT failed.
- **Session isolation:** GET /audit returns only rows WHERE `session_id` = the requesting `X-Session-ID`. Rows from other sessions are never returned.
- **Ordering:** GET /audit returns rows ordered by `created_at DESC` (newest first).
- **Retention:** All `audit_log` rows are kept indefinitely in Phase 1 (no TTL or pruning).
- **Immutability:** `audit_log` rows are never updated after insertion.

## Success Criteria

- [ ] After a successful POST /query, one audit_log row exists with non-null sql_generated, row_count, duration_ms, and null error
- [ ] After a failed POST /query (502), one audit_log row exists with a non-null error field
- [ ] GET /audit returns all audit_log rows for the session in newest-first order
- [ ] GET /audit for session A does not return rows belonging to session B
- [ ] An audit_log INSERT failure does not cause POST /query to return an error — the 200 response is still returned
- [ ] `audit_id` in the POST /query response matches the `id` of the audit_log row in GET /audit
