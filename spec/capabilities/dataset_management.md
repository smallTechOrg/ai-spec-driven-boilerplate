# Capability: Dataset Management

## What It Does

Accepts a CSV or Excel file upload from the browser, parses it into a pandas DataFrame, and ingests it as a session-namespaced SQLite table that the NL Query capability can query.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `file` | Multipart file upload (.csv or .xlsx) | Browser file picker → POST /datasets/upload | Yes |
| `session_id` | UUID string | X-Session-ID request header | Yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| Dataset metadata | JSON object (id, session_id, table_name, original_filename, row_count, column_names, created_at) | POST /datasets/upload response body |
| Dynamic SQLite table | SQLite table named `{session_id_underscored}_{sanitized_filename}` | SQLite DB (./data/agent.db) |
| `datasets` ORM row | SQLite row in `datasets` table | SQLite DB |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | `DataFrame.to_sql(table_name, engine, if_exists="replace", index=False)` | Return 422 with parse/ingest error detail |
| SQLite | INSERT into `datasets` table | Return 500 |
| SQLite | UPSERT into `sessions` table (create or update last_seen_at) | Return 500 |

## Business Rules

- Accepted file types: `.csv` and `.xlsx` only. Any other extension returns 422 immediately (before reading the file).
- Row limit: files with more than 500,000 rows are rejected with 422. The row count is checked after parsing, before `DataFrame.to_sql()` is called.
- Empty files (zero data rows after header) return 422.
- Files that fail to parse (corrupt CSV, unreadable Excel) return 422 with the pandas exception message.
- Table naming: `{session_id_underscored}_{sanitized_name}` where `session_id_underscored` replaces all hyphens in the UUID with underscores, and `sanitized_name` is the filename stem (no extension) lowercased with all non-alphanumeric characters replaced by underscores, leading/trailing underscores stripped.
- If a file with the same sanitized name is re-uploaded in the same session, the dynamic table is replaced (`if_exists="replace"`) and a new `datasets` row is inserted (the old row is not deleted in Phase 1).
- The `sessions` row for the given `session_id` is upserted on every upload: created if it does not exist, `last_seen_at` updated if it does.
- No file is written to the filesystem — data lives entirely in the SQLite dynamic table.

## Success Criteria

- [ ] POST /datasets/upload with a valid CSV returns 200 with correct metadata (id, table_name, row_count, column_names) within 5 seconds for files up to 10 MB
- [ ] The dynamic SQLite table is queryable by name after a successful upload
- [ ] POST /datasets/upload with a .json file returns 422
- [ ] POST /datasets/upload with a CSV exceeding 500,000 rows returns 422
- [ ] POST /datasets/upload with an empty CSV (header only) returns 422
- [ ] POST /datasets/upload without X-Session-ID returns 422
- [ ] GET /datasets returns the uploaded dataset in the list for the same session_id
- [ ] GET /datasets with a different session_id does not return the dataset (empty array)
