# Capability: Ingest & Profile a Dataset

## What It Does
Loads one CSV or Excel file (each Excel sheet as its own dataset) into the local query engine and auto-generates a data profile, with no code from the user.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| file | CSV or `.xlsx` (≤ ~100 MB) | multipart upload (`POST /api/datasets`) | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| dataset entry/entries | one per CSV or per Excel sheet (id, name, kind, row_count) | API response + library (SQLite) |
| profile | rows, columns + types, null counts, basic per-column stats | API response + cached on the dataset (SQLite) |
| loaded table | the rows loaded into the local query engine | local store (not returned) |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Local query engine (DuckDB) | load file + run profile queries | return `api_error` (400 parse / 500 load) |

## Business Rules
- CSV is read directly by the query engine; Excel sheets are parsed and each sheet registered as its own dataset.
- Profiling uses only local queries — no data leaves the machine at any point in this capability.
- The profile is cached on the dataset so re-display is instant.
- Non-destructive: the source file is never modified.

## Success Criteria
- [ ] Uploading the shipped sample CSV returns a profile with the correct row count, column names, types, and per-column null counts.
- [ ] Uploading an `.xlsx` with two sheets returns two dataset entries, one per sheet.
- [ ] A file over the max size is rejected with a clear error (not a crash).
- [ ] No raw row value appears in any LLM prompt during ingest/profile (covered by the privacy-boundary test).
