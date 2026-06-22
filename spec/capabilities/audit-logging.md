# Capability: Audit Logging

## What It Does
Records every SQL/data operation (ingest and query) to a durable audit log for compliance. Write-only in v1; the audit UI is Phase 5.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| operation context | {operation, sql, status, row_count, error, duration_ms} | ingest / execute_sql node | yes |
| session_id, dataset_id | str | request context | no (nullable) |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| audit entry | AuditLog row | metadata DB |

## External Calls
| System | Operation | On Failure |
|--------|-----------|-----------|
| Metadata DB | insert AuditLog row | log error; never block the user's response |

## Business Rules
- Written on BOTH success and failure of any data operation.
- Captures sql_text, status, row_count, error_message, duration_ms.
- The full audit-log schema exists from Phase 1 even though the UI is Phase 5.

## Success Criteria
- [ ] Every query execution produces exactly one AuditLog row with the correct status.
- [ ] A failed SQL execution writes an AuditLog row with status=error and the error_message.
- [ ] An ingest writes an AuditLog row with operation=ingest and the row count.
