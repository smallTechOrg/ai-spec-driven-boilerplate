# Capability: Natural-Language Query

## What It Does
Turns a natural-language question about a dataset into SQL, executes it, and returns a formatted answer plus a result table.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| question | str | chat composer | yes |
| dataset_id | str | selected dataset | yes |
| session_id | str | active session | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| answer | str (prose) | assistant Message + UI |
| result table | {columns, rows} | assistant Message + UI |
| sql | str | assistant Message ("View SQL") + AuditLog |

## External Calls
| System | Operation | On Failure |
|--------|-----------|-----------|
| Gemini | generate SQL from question + schema | QUERY_FAILED surfaced to UI |
| DuckDB | execute read-only SELECT | AuditLog(status=error); QUERY_FAILED |
| Gemini | format answer from capped result preview | QUERY_FAILED |

## Business Rules
- Only column names/types are sent to Gemini for SQL generation — never row data.
- The generated statement must be a single read-only SELECT; non-SELECT is rejected.
- `format_answer` receives at most the first 50 result rows + total row count.
- Every execution writes an AuditLog(operation=query) (success or error).
- Exactly two Gemini calls on the happy path (generate SQL, format answer).

## Success Criteria
- [ ] A question like "total revenue by region" returns a correct prose answer and a matching result table against real Gemini.
- [ ] The executed SQL is stored on the message and in the AuditLog.
- [ ] No row data from the dataset appears in the SQL-generation prompt.
- [ ] A non-SELECT or failing query yields a friendly error in the UI and an AuditLog error row (no hung UI).
