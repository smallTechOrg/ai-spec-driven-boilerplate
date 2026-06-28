# Capability: Dataset Library & Cross-Day Restore

> **DEFERRED — Phase 2.** In Phase 1 the library sidebar and session-restore are LABELLED stubs. This file specifies the target behaviour.

## What It Does
Persists loaded datasets in a library and restores the conversation/run history and the previously-loaded dataset across days, so the user resumes where they left off — "load once, ask many."

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| (none for restore) | — | on-boot SQLite + on-disk DuckDB | — |
| dataset selection / delete | dataset_id | UI (library sidebar) | yes (for select/delete) |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| library list | datasets with profiles | `GET /api/datasets` → sidebar |
| restored session | active dataset + conversation history | `GET /api/session` → UI on load |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | list/select/delete datasets; load session + messages | `api_error` |
| DuckDB (on-disk per dataset) | reload persisted tables on boot | re-ingest from source path |

## Business Rules
- DuckDB tables persist on disk per dataset so reload survives restart.
- Deleting a library dataset drops its DuckDB table and cleans its source file; Runs/Messages retained for audit.
- Conversation history is threaded into the plan prompt (bounded sliding window).

## Success Criteria
- [ ] After a restart, both previously-uploaded datasets re-appear in the library and prior Q&A history is restored (integration test asserts survival across a process restart).
- [ ] Selecting a library dataset makes it the active dataset for the next ask.
- [ ] Privacy boundary still holds — restore moves no raw rows to any LLM.
