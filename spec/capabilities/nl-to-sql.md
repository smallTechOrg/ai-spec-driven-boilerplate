# Capability: NL-to-SQL

## What It Does

Accepts a natural-language question, builds a schema context from all tables available in the session (uploaded and pre-existing), calls the LLM to generate a SQL SELECT statement, validates the SQL, executes it against SQLite, and returns the result rows. Caches results by `(question_hash, table_hash)` to avoid redundant LLM calls.

## Inputs

| Input | Type | Source | Required |
|-------|------|---------|----------|
| `session_id` | string (UUID) | URL path parameter / agent state | Yes |
| `question` | string | HTTP request body / agent state | Yes |
| Available tables | list of `uploaded_files` rows | `uploaded_files` DB table | Yes |
| Cached result | `analysis_cache` row (if present) | `analysis_cache` DB table | No |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `sql_query` | string | agent state `sql_query`; stored in `runs.sql_query` |
| `query_rows` | list[dict] | agent state `query_rows` |
| Cache write | `analysis_cache` row | `analysis_cache` table (on cache miss) |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini LLM | Generate SQL from schema context + question | Set `state.error`; route to `handle_error` |
| SQLite (via SQLAlchemy) | `EXPLAIN QUERY PLAN <sql>` (validation) | Return validation error; do not execute |
| SQLite (via SQLAlchemy) | `SELECT ...` (execution) | Set `state.error`; route to `handle_error` |

## Business Rules

- **Schema context construction:** for each table in the session, include: table name, column names + inferred types, and up to **20 sample rows** (random sample). Total context passed to the LLM is capped at the equivalent of 1 000 rows of serialized data; if schema + sample exceeds this, reduce sample rows proportionally.
- **Cache lookup:** compute `question_hash = sha256(question.strip().lower())` and `table_hash = sha256(sorted list of table names + their row counts)`. If a matching row exists in `analysis_cache`, return its `result_json` directly without calling the LLM.
- **SQL validation:** run `EXPLAIN QUERY PLAN <sql>` before execution. If this throws, set `state.error = "invalid_sql: <reason>"` and abort — never execute unvalidated SQL.
- **SQL restrictions:** only `SELECT` statements are permitted. Any generated SQL containing `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`, or `ATTACH` is rejected with `forbidden_sql_operation`.
- **Result size cap:** return at most **10 000 rows** from execution. If the query would return more, prepend `SELECT * FROM (<original>) LIMIT 10000` automatically and note the truncation in `state.report_json`.
- On cache miss, store the result in `analysis_cache` after successful execution.
- The LLM system prompt instructs the model to return **only** the SQL statement, no prose, no markdown fences. A post-processing step strips any accidental markdown wrappers.

## Success Criteria

- [ ] A question about an uploaded CSV produces a valid, executable SQL query that returns the expected rows.
- [ ] A second identical question (same session, same tables) returns the cached result without making a Gemini API call (verified by asserting `analysis_cache` row count increases only on first call).
- [ ] A question whose generated SQL contains `DROP TABLE` is rejected with `forbidden_sql_operation` before execution.
- [ ] SQL that fails `EXPLAIN QUERY PLAN` (e.g. references a nonexistent column) is rejected with `invalid_sql` and does not reach `execute_sql`.
- [ ] A query returning more than 10 000 rows is silently capped to 10 000 and the truncation flag is present in state.
- [ ] The schema context sent to the LLM contains at most 20 sample rows per table.
