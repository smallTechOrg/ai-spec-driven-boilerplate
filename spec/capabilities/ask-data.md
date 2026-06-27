# Capability: Ask Data (Answer + Chart, rows stay local)

## What It Does
Answers a plain-English question about an uploaded dataset with a plain-English answer plus a chart, computing the answer over the full dataset locally and sending only schema + aggregates to the LLM.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| dataset_id | string | prior upload (returned by upload) | yes |
| question | string | chat box | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| answer_text | string | answer panel |
| chart_spec | object `{type, x, series}` | chart render |
| question record | row | app store (SQLite) |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| DuckDB (local) | profile schema; run full-data aggregation | set error → `COMPUTE_FAILED`, do not crash |
| Gemini 2.5 Flash | plan aggregation (schema only); phrase answer (aggregate only) | set error → `LLM_UNAVAILABLE` |

## Business Rules
- Only schema + computed aggregates may be sent to the LLM — never raw rows, columns, or samples (enforced by `assert_no_raw_rows`).
- The answer is computed over the FULL dataset locally, never over a sample.
- At most two LLM calls per question (plan + phrase); aim for one when trivially mappable.

## Success Criteria
- [ ] Upload a CSV, ask "total revenue by region" → correct answer + bar chart.
- [ ] `test_privacy_boundary` confirms no raw cell value reaches the LLM payload.
- [ ] `test_full_data` (fixture where sample ≠ full) returns the full-data answer.
- [ ] The run persists a question record with answer + chart spec.
