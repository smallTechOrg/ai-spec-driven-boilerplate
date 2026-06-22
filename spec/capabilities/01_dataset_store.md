# Capability: Dataset Store and Organise

## What It Does

Accepts a user-uploaded CSV or Excel file, persists it to disk, registers it as a named DuckDB table, and stores its metadata (name, description, schema, row count, upload timestamp) in the SQLite dataset catalogue.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| file | multipart/form-data binary | HTTP upload request | Yes |
| name | string (1–100 chars) | HTTP upload request body | Yes |
| description | string (0–500 chars) | HTTP upload request body | No |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| dataset_id | UUID string | HTTP response body; SQLite `datasets` row |
| name | string | HTTP response body; SQLite `datasets` row |
| description | string or null | HTTP response body; SQLite `datasets` row |
| table_name | string (slugified) | SQLite `datasets` row; DuckDB table registry |
| schema | JSON array of `{column, dtype}` | HTTP response body; SQLite `datasets` row |
| row_count | integer | HTTP response body; SQLite `datasets` row |
| file_path | string | SQLite `datasets` row |
| upload_timestamp | ISO-8601 datetime | HTTP response body; SQLite `datasets` row |
| is_active | boolean (true) | SQLite `datasets` row |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Local filesystem | Write file to `data/uploads/<dataset_id>.<ext>` | Return HTTP 500; do not write catalogue row |
| pandas / openpyxl | Parse file to infer schema and count rows | Return HTTP 422 with parse error message; delete partially-written file |
| SQLite (via SQLAlchemy) | INSERT into `datasets` table | Return HTTP 500; log error |
| DuckDB | `CREATE OR REPLACE VIEW <table_name> AS SELECT * FROM read_csv_auto(...)` or `read_parquet` / `read_excel` equivalent | Return HTTP 500; log error; roll back catalogue insert |

## Business Rules

- Accepted MIME types / extensions: `.csv`, `.xlsx`, `.xls`. Any other extension returns HTTP 415.
- Maximum file size: 200 MB. Requests exceeding this limit return HTTP 413.
- `table_name` is derived from `name` by lowercasing, replacing non-alphanumeric characters with underscores, and truncating to 63 characters. If the resulting name collides with an existing active dataset's `table_name`, a numeric suffix (`_2`, `_3`, …) is appended.
- Files are stored at `data/uploads/<dataset_id>.<original_extension>` and are **never deleted automatically**.
- Schema inference uses pandas `dtype` mapping; all columns are recorded even if dtype is `object`.
- Row count is the exact count from the parsed DataFrame, not an estimate.
- A failed upload (any stage after file write) must clean up the orphaned file from disk.
- Soft-deleted datasets (`is_active = false`) are excluded from the catalogue list and from DuckDB at next server restart, but the file is never removed.

> **Assumed:** Excel files with multiple sheets: only the first sheet is loaded. The user is informed of this in the API response via an `info` field.

## Success Criteria

- [ ] Uploading a valid CSV returns HTTP 201 with a response body containing `dataset_id`, `name`, `schema` (array with correct column names and types), `row_count` (exact), and `upload_timestamp`.
- [ ] The file is present on disk at `data/uploads/<dataset_id>.csv` after upload.
- [ ] A row exists in the SQLite `datasets` table with all fields populated correctly.
- [ ] DuckDB can `SELECT COUNT(*) FROM <table_name>` and return the correct row count immediately after upload.
- [ ] Uploading a `.xlsx` file succeeds and registers the first sheet only.
- [ ] Uploading an empty file (0 rows, header only) returns HTTP 201 with `row_count = 0` and an empty schema is not accepted — columns must be present; a completely empty file (no header) returns HTTP 422.
- [ ] Uploading a file larger than 200 MB returns HTTP 413.
- [ ] Uploading a file with an unsupported extension returns HTTP 415.
- [ ] Uploading a malformed CSV (unparseable) returns HTTP 422 with a descriptive error message.
- [ ] Two datasets with the same name get distinct `table_name` values (suffix applied).
