# Capability: NL Query

## What It Does

Accepts a natural-language question and a dataset table name, generates a SQLite SELECT query via Gemini tool-use, executes it against the named SQLite table, and returns the answer text and result rows.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `question` | string | POST /query request body | Yes |
| `dataset_table` | string (SQLite table name) | POST /query request body | Yes |
| `session_id` | UUID string | X-Session-ID request header | Yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `answer` | string (markdown) | POST /query response body |
| `table` | list of dicts (capped at 1,000 rows) | POST /query response body |
| `sql` | string | POST /query response body |
| `audit_id` | UUID string | POST /query response body |
| Error message | string | POST /query response body (502) |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | `PRAGMA table_info({dataset_table})` via SQLAlchemy text() | Set state["error"], return 502 |
| Gemini API | `generate_content` with `generate_sql` tool, tool_config mode=ANY | Retry 3× with backoff; after 3 failures set state["error"], return 502 |
| SQLite | `sqlalchemy.text(sql)` execute | Set state["error"], return 502 |
| SQLite | INSERT into `audit_log` | Non-fatal — log warning, continue |

## Business Rules

- Cross-session access protection: `dataset_table` must start with `{session_id_underscored}_` (the X-Session-ID with hyphens replaced by underscores). If it does not match, return 403 immediately — before graph invocation.
- Dataset existence check: `dataset_table` must exist in the `datasets` ORM table with the matching `session_id`. Return 404 if not found.
- Schema-aware prompting: `query_planner` runs `PRAGMA table_info({dataset_table})` and injects the result as schema context into the Gemini prompt. Raw dataset rows are never sent to Gemini.
- Forced tool use: Gemini is called with `tool_config={"function_calling_config": {"mode": "ANY"}}` so it must return a `generate_sql` function call. Plain-text responses are treated as errors.
- SQL validation: the SQL string extracted from the tool call must begin with `SELECT` (case-insensitive). Non-SELECT SQL (INSERT, UPDATE, DROP, etc.) sets `state["error"]` and returns 502.
- Result cap: `sql_executor` fetches at most 1,000 rows from SQLite. `row_count` reflects the number of rows actually returned (≤ 1,000).
- Retry: `query_planner` retries the Gemini call up to 3 times on API exception (1 s / 2 s / 4 s backoff). After 3 failures, sets `state["error"]` and returns 502.
- Audit log: one `audit_log` row is always written per `POST /query`, regardless of success or failure. An `audit_log` INSERT failure is non-fatal.

## Success Criteria

- [ ] POST /query with a valid question and dataset_table returns 200 with non-empty `answer`, `table`, and `sql` fields
- [ ] The `sql` field contains a valid SQLite SELECT statement referencing the correct dataset_table
- [ ] The `table` field contains at most 1,000 rows
- [ ] POST /query with a dataset_table from a different session returns 403
- [ ] POST /query with a dataset_table that does not exist in this session returns 404
- [ ] POST /query with a blank question returns 422
- [ ] When Gemini returns a non-SELECT SQL, POST /query returns 502 with an error message
- [ ] An `audit_log` row exists after every POST /query call (success or failure)
