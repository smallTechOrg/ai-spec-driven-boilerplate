# Capability: Connect PostgreSQL (live source, rows stay local)

## What It Does
Lets the user connect a PostgreSQL database via a connection string and ask the same plain-English questions, with row-level computation running locally (DuckDB scanning Postgres) and only schema + aggregates sent to the LLM.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| connection_string | string | "Connect PostgreSQL" form | yes |
| question | string | chat box | yes |
| connection_id | string | prior connect (returned by connect) | yes (for ask) |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| connection record | row | app store (SQLite) |
| answer_text + chart_spec | string + object | answer panel + chart |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| PostgreSQL (user-supplied) | introspect schema; DuckDB scans for aggregation (read-only) | `SOURCE_UNREACHABLE` at connect; `COMPUTE_FAILED` at ask |
| Gemini 2.5 Flash | plan + phrase (schema/aggregates only) | `LLM_UNAVAILABLE` |

## Business Rules
- The connection string is stored only in the local app store; it is never sent to the LLM.
- Aggregation runs locally via DuckDB's postgres scan; no raw rows leave the machine and none reach the LLM.
- Read-only — DataChat never writes to the user's database.

## Success Criteria
- [ ] Paste a valid connection string → validated, schema introspected.
- [ ] Ask a question against the live DB → answer + chart with rows staying local.
- [ ] `test_pg_privacy` confirms no Postgres row appears in the LLM payload.
