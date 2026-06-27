# Capability: File Upload

## What It Does
Accepts a user-uploaded CSV or Excel file, parses it with pandas, stores the file and its metadata (schema, sample rows, row count) in SQLite, and returns a dataset ID the analysis capability uses.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| file | multipart/form-data binary | HTTP POST /datasets, field `file` | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| dataset_id | string (UUID) | HTTP response body, stored in SQLite datasets table |
| filename | string | HTTP response body |
| columns | array of {name, dtype} | HTTP response body |
| row_count | integer | HTTP response body |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Local filesystem (data/uploads/) | Write uploaded file | 500 — upload fails with clear error message |
| SQLite (datasets table) | INSERT dataset metadata | 500 — dataset not saved |

## Business Rules
- Accept only .csv, .xlsx, .xls files; reject all others with HTTP 422
- Store the file at `data/uploads/{dataset_id}_{filename}` (directory created at startup if missing)
- Extract columns using `df.dtypes` — store as JSON array of `{name: str, dtype: str}` (dtype as string, e.g. "int64", "object")
- Store first 20 rows as `sample_rows_json` using `df.head(20).to_dict(orient="records")`
- Store total row count using `len(df)` against the full DataFrame
- dataset_id is a UUID4 generated at upload time

## Success Criteria
- [ ] POST /datasets with a valid CSV returns 200 with dataset_id, filename, columns array, and row_count
- [ ] POST /datasets with a valid Excel (.xlsx) returns 200 with correct schema
- [ ] POST /datasets with a .txt file returns 422
- [ ] Uploaded file exists on disk at `data/uploads/{dataset_id}_{filename}` after a successful upload
- [ ] SQLite datasets row created with all fields populated (columns_json, sample_rows_json, row_count, file_path, created_at)
