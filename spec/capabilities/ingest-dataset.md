# Capability: Ingest Dataset
## What It Does
Ingests an uploaded CSV/Excel file into a local DuckDB table and records a persistent dataset descriptor (schema, row count, capped sample preview) under the active session.
## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| file | multipart upload (.csv/.xlsx) | `POST /datasets` | yes |
| session_id | string | form field (defaults to default session) | no |
## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| Dataset descriptor (id, name, row_count, schema, sample_rows) | JSON | `POST /datasets` response → Datasets panel |
| Dataset rows | DuckDB table | `AGENT_DUCKDB_PATH` |
| DatasetRow + (auto) SessionRow | metadata rows | SQLite (`datasets`, `sessions`) |
## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| DuckDB | Create table from parsed frame | 500, no dataset recorded |
| pandas/openpyxl | Parse CSV/Excel | 400 (unparseable/unsupported) |
## Business Rules
- Only `.csv` and `.xlsx` accepted; anything else → 400.
- An empty file (zero data rows) → 400.
- `sample_rows_json` stores at most `AGENT_MAX_SAMPLE_ROWS` rows — the only rows ever exposed to the LLM.
- DuckDB table name is sanitized and unique; rows never written to the metadata DB.
## Success Criteria
- [ ] Uploading a valid CSV creates exactly one DuckDB table whose row count equals the file's data rows.
- [ ] The returned `schema` lists every column with an inferred type.
- [ ] `sample_rows` length ≤ `AGENT_MAX_SAMPLE_ROWS`.
- [ ] After a server restart, `GET /datasets` still returns the dataset.
- [ ] Uploading a `.txt` file returns 400 and records no dataset.
