# Capability: dataset_library

## What It Does
Lets the single user upload CSV/Excel files (up to ~100MB), auto-profiles each one locally without sending rows to the LLM, and persists them in a library they return to across days (P4: several similarly-shaped files or a folder analyzed as one dataset).

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| file | multipart upload (CSV/.xlsx) | browser upload | yes |
| name | string | user (optional label) | no |
| dataset_id | string | path (fetch/list/delete) | for read/delete |
| member files | list of files / folder | browser (P4 multi-file) | P4 only |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| Dataset record | row | `datasets` ([data.md](../data.md)) + file on `data/uploads/` |
| Profile | columns/dtypes/ranges/row count (+P3 quality flags) | `dataset_profiles`; returned to UI |
| Library list | array of datasets | `GET /datasets` → Library rail |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Local filesystem | save file, read with pandas to profile | surface upload error; no partial row persisted |
| (none — Gemini is NOT called here) | profiling is purely local | n/a |

## Business Rules
- Profiling reads the file locally with pandas; **only** schema-level metadata (no raw rows) is persisted or ever shown to the LLM.
- Supported types: `.csv`, `.xlsx` (Excel via openpyxl). Unsupported/oversized/unreadable → a clear 400.
- Datasets persist across server restarts (file on disk + row in SQLite).
- P3: profiling also computes data-quality flags (nulls, dupes, outliers) per column.
- P4: a `group` dataset references multiple similarly-shaped files loaded together (concat/join); its profile reflects the combined data.

## Success Criteria
- [ ] Uploading a CSV creates a dataset + a profile with correct column list, dtypes, ranges, and row count.
- [ ] The profiling step makes **zero** Gemini calls (asserted — no outbound LLM request during profile).
- [ ] After a server restart the dataset still appears in `GET /datasets` and is re-selectable (P2).
- [ ] An `.xlsx` upload profiles correctly via pandas+openpyxl.
- [ ] P4: a group of two files profiles with a combined row count equal to the sum (minus dedupe, per join rule).
