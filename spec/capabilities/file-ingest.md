# Capability: File Ingest

## What It Does

Accepts a CSV or Excel file upload, parses it into a pandas DataFrame, creates (or replaces) a named SQLite table from the data, and stores the file metadata — table name, row count, column names — in the `uploaded_files` record for the session.

## Inputs

| Input | Type | Source | Required |
|-------|------|---------|----------|
| `session_id` | string (UUID) | URL path parameter | Yes |
| `file` | multipart/form-data | HTTP request body | Yes |
| File content | CSV or Excel (`.csv`, `.xlsx`, `.xls`) | uploaded binary | Yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `table_name` | string | JSON response + `uploaded_files.table_name` |
| `row_count` | integer | JSON response + `uploaded_files.row_count` |
| `columns` | list[string] | JSON response + `uploaded_files.column_names` (JSON) |
| SQLite table | DDL table created in the agent DB | SQLite data file |
| `uploaded_files` row | ORM row | `uploaded_files` table |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite (via SQLAlchemy) | `DROP TABLE IF EXISTS` + `CREATE TABLE` (via pandas `to_sql`) | Return HTTP 500 with `ingest_failed` error code; do not leave partial table |
| pandas | `read_csv` / `read_excel` | Return HTTP 422 with `parse_failed` error code |

## Business Rules

- Table name is derived from the filename: lowercase, non-alphanumeric characters replaced with `_`, stripped of extension. Example: `Sales Report Q1.xlsx` → `sales_report_q1`.
- If a table with that name already exists for the session, it is dropped and recreated (re-upload replaces).
- Maximum file size: **50 MB**. Requests exceeding this limit receive HTTP 413.
- Maximum row count after parsing: **500 000 rows**. Files exceeding this limit are rejected with HTTP 422 and `too_many_rows` error.
- Only `.csv`, `.xlsx`, `.xls` extensions are accepted. Other extensions receive HTTP 422 with `unsupported_format`.
- The binary file content is **not stored on disk** after ingest — only the SQLite table and the `uploaded_files` metadata row persist.
- Column names are sanitized to valid SQLite identifiers (non-alphanumeric → `_`, reserved words prefixed with `col_`).
- All ingested tables are accessible from the SQL generation surface alongside any pre-existing DB tables.

## Success Criteria

- [ ] Uploading a valid CSV returns `{table_name, row_count, columns}` with HTTP 200.
- [ ] The resulting SQLite table has the correct columns and row count (`SELECT COUNT(*) FROM <table_name>` matches `row_count`).
- [ ] Re-uploading a file with the same name replaces the existing table; subsequent `SELECT COUNT(*)` reflects the new row count.
- [ ] A file exceeding 50 MB returns HTTP 413 before parsing begins.
- [ ] A file with more than 500 000 rows returns HTTP 422 with `too_many_rows`.
- [ ] An unsupported file extension returns HTTP 422 with `unsupported_format`.
- [ ] After ingest, `GET /sessions/{session_id}/files` lists the ingested file with correct metadata.
