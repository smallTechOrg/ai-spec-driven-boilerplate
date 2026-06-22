# Capability: Audit Log

## What It Does

Appends a structured record to the audit log after every SQL execution, capturing the question, generated SQL, datasets touched, result size, and latency, to provide a complete tamper-evident history of all data operations.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| session_id | UUID string | Active session | Yes |
| user_question | string | Chat API request | Yes |
| generated_sql | string or null | NL→SQL capability | Yes |
| datasets_touched | array of table_name strings | NL→SQL capability | Yes |
| row_count_returned | integer | DuckDB execution result | Yes |
| latency_ms | integer | Wall-clock time from question receipt to response ready | Yes |
| sql_error | string or null | DuckDB execution error message, if any | No |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| audit_entry_id | UUID string | SQLite `audit_log` row |
| logged_at | ISO-8601 datetime | SQLite `audit_log` row |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite (via SQLAlchemy) | INSERT into `audit_log` table | Log error to stdout; do NOT raise exception to caller — audit log failure must not break the chat response |

## Business Rules

- **Append-only:** No UPDATE or DELETE statements are ever issued against `audit_log`. There is no admin endpoint to delete entries. The SQLite file permissions should be set to allow writes but the application never issues any non-INSERT DML on this table.
- An audit entry is written for every turn in which `execute_sql` was called at least once, regardless of whether the SQL succeeded or failed.
- If `generated_sql` is null (e.g., Gemini asked a clarifying question with no tool calls), no audit entry is written for that turn.
- If multiple `execute_sql` calls occur in one turn (sub-queries), a single audit entry is written covering all SQL in that turn. `generated_sql` contains the last executed SQL statement; `datasets_touched` is the union of all tables referenced across all calls in the turn.
- `latency_ms` is measured from the moment the chat endpoint receives the request to the moment the response is assembled (includes Gemini API time + DuckDB execution time).
- Audit entries are never returned to the frontend. They are accessible only via direct SQLite inspection or a future admin endpoint (out of scope for v1).
- `sql_error` is populated with the DuckDB error message string if execution failed; null otherwise.

> **Assumed:** A single audit entry per chat turn (not per tool call) is simpler and sufficient for v1. Per-tool-call granularity is deferred to v2.

## Success Criteria

- [ ] After a successful NL question that triggers SQL execution, exactly one row is present in `audit_log` with the correct `session_id`, `user_question`, `generated_sql`, non-empty `datasets_touched`, correct `row_count_returned`, and a positive `latency_ms`.
- [ ] After a failed SQL execution (e.g., DuckDB syntax error), an audit entry is written with `sql_error` populated and `row_count_returned = 0`.
- [ ] A clarifying-question turn (no SQL generated) produces zero new `audit_log` rows.
- [ ] Attempting to run a DELETE statement against `audit_log` in tests confirms the application code contains no such path (code review check; not a runtime assertion).
- [ ] An audit log write failure (simulated by temporarily making the table unwritable or patching the session) does not cause the chat API to return an error — the response is still returned to the client.
- [ ] `logged_at` is within 1 second of the time the chat API returned its response (verified in integration tests).
