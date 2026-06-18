# Capability: Upload CSV(s) into a Dataset

## What It Does

Creates a named dataset and loads one or more uploaded CSV files into it — parsing each file,
inferring its column schema and types, and materializing the rows as a queryable table in DuckDB.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| dataset name | string | user (create-dataset request) | yes |
| CSV file(s) | multipart file upload | user (upload request) | yes |
| dataset id | uuid | from create-dataset, used on upload | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| dataset record | row in `dataset` (SQLite) | persistence |
| file record + inferred schema | row in `file` (columns + types JSON) | persistence |
| DuckDB table | one table per file, named from the dataset/file | DuckDB analytical engine |
| schema summary | JSON (columns, types, row count) | API response → UI |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | insert dataset + file rows | fail loud → `api_error("DB_ERROR", …, 500)` |
| DuckDB | `read_csv_auto` / register table; `DESCRIBE` for inferred types | parse/load error → `api_error("CSV_PARSE_ERROR", detail, 400)`; file rejected, dataset left intact |

## Business Rules

- **CSV only.** Reject any non-CSV upload with `api_error("UNSUPPORTED_FORMAT", …, 400)`.
- A dataset may hold **multiple files**; each becomes its own DuckDB table. (Cross-file joins are out
  of scope — see [`../01-vision.md`](../01-vision.md).)
- Schema (column name + inferred type) is **inferred automatically**, never hand-entered, and stored
  on the `file` record so it can be shown to the user and assembled into agent context.
- Data is assumed to **fit in memory**; oversized files are out of scope for v1.
- A small **row sample** (≤20 rows) is captured per file for LLM grounding — the full data is never
  sent to the LLM ([`../01-vision.md`](../01-vision.md) § Key Constraints).

## Success Criteria

- [ ] Creating a dataset then uploading a valid CSV returns the inferred schema (each column name +
      type) and a non-zero row count.
- [ ] Uploading a second CSV into the same dataset adds a second queryable table without disturbing
      the first.
- [ ] Uploading a non-CSV (e.g. `.json`, `.xlsx`) returns `UNSUPPORTED_FORMAT` (400), and the dataset
      is unchanged.
- [ ] A malformed CSV returns `CSV_PARSE_ERROR` (400) with a usable detail message, not a 500.
- [ ] After upload, the dataset's DuckDB table is queryable by a read-only `SELECT` (verified by the
      `run_sql` MCP tool).
