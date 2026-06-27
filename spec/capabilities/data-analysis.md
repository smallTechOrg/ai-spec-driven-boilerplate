# Capability: Data Analysis

## What It Does
Accepts a dataset ID and a plain-English question, invokes the LangGraph analyze_data node which uses Gemini to generate pandas code, executes that code against the full local DataFrame, and returns a chart type, real computed labels and values, and a written summary.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| dataset_id | string (UUID) | HTTP POST /analyze request body | yes |
| question | string | HTTP POST /analyze request body | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| chart_type | string ("bar" or "line" or "scatter") | HTTP response body |
| labels | array | HTTP response body — real values from pandas execution |
| values | array | HTTP response body — real values from pandas execution |
| summary | string | HTTP response body |
| dataset_id | string | HTTP response body (echoed) |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite (datasets table) | SELECT dataset by dataset_id | 404 if not found |
| Local filesystem (data/uploads/) | Read full CSV/Excel file via pandas | 500 — analysis fails with error message |
| Gemini 2.5 Pro API | Generate pandas code + chart config + summary | 500 — analysis fails; user sees error message |

## Business Rules
- Privacy rule: Gemini receives ONLY the column schema (name + dtype) and up to 20 sample rows as CSV text — the full dataset is NEVER sent to Gemini
- The backend loads the full DataFrame with pandas from the stored file path
- Gemini returns a JSON object with exactly these fields: `pandas_code`, `chart_type`, `labels`, `values`, `summary`
- Gemini's `labels` and `values` are illustrative only — they are DISCARDED after pandas execution
- The backend executes `pandas_code` in a restricted namespace: `{"df": df, "pd": pd}` — no other imports allowed
- `pandas_code` must assign its result to a variable named `result` which is a dict with keys `labels` (list) and `values` (list)
- The real `labels` and `values` from `namespace["result"]` replace Gemini's illustrative values in the response
- chart_type must be one of "bar", "line", "scatter"; default to "bar" if Gemini returns an unrecognized value
- On any Gemini error or pandas execution error, set state["error"] and return HTTP 500

## Success Criteria
- [ ] POST /analyze with a valid dataset_id and question returns 200 with chart_type, non-empty labels array, non-empty values array, and non-empty summary string
- [ ] The labels and values in the response are computed from the full dataset, not from Gemini's illustrative values
- [ ] Gemini is never called with more than the column schema + 20 sample rows (verifiable by inspecting the prompt in test)
- [ ] POST /analyze with a nonexistent dataset_id returns 404
- [ ] Gemini API failure returns HTTP 500 with a clear error message
- [ ] pandas_code execution error returns HTTP 500 with a clear error message
