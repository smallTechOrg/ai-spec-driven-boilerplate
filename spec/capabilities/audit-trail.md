# Capability: Audit Trail
## What It Does
Persists and exposes a permanent, viewable, exportable log of every data operation (each ask): timestamp, NL question, generated SQL, row count, duration, and status.
## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| (operation metadata) | fields | written by the Ask Question capability | yes |
| session_id | string | `GET /audit` / `GET /audit/export` query | no |
| format | string (`csv`\|`json`) | `GET /audit/export` query | no |
## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| Audit entries (newest first) | JSON list | `GET /audit` → Audit Log panel |
| Exported audit file | CSV/JSON download | `GET /audit/export` |
## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite (`audit_logs`) | Insert on each ask; read on list/export | 500 |
## Business Rules
- One audit row per ask, including failed asks (status `failed`, with `error_message`).
- Audit rows are immutable and never auto-expired — the trail is permanent.
- Each row records timestamp, nl_question, generated_sql, row_count, duration_ms, status.
## Success Criteria
- [ ] After N asks, `GET /audit` returns N entries ordered newest-first.
- [ ] Every entry has a non-null timestamp, nl_question, row_count, duration_ms, and status.
- [ ] Entries survive a server restart (persisted in SQLite).
- [ ] `GET /audit/export?format=csv` downloads a CSV with one row per audit entry plus a header.
