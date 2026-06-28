# Capability: Cost Rollup, Derived Tables & Reproducible Re-run

> **DEFERRED — Phase 5.** In Phase 1 the daily-cost total and re-run are LABELLED stubs. This file specifies the target behaviour.

## What It Does
Closes out transparency and durability: a running daily-total cost rollup, user-named saved derived tables that persist as reusable datasets, and a reproducible one-click re-run of any historical query from the audit log.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| date scope | day (default today) | UI / `GET /api/cost/daily` | no |
| derive request | run_id + new table name | UI (`POST /api/datasets/{id}/derive`) | yes (to save) |
| rerun request | run_id | UI (`POST /api/runs/{id}/rerun`) | yes (to re-run) |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| daily total | summed est_usd + token counts for the day | `GET /api/cost/daily` → top bar |
| derived table | a materialized query result as a reusable DuckDB table + library entry | library |
| reproduced answer | rich-answer envelope from re-executing stored SQL | `POST /api/runs/{id}/rerun` |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | sum Run costs; read stored SQL | `api_error` |
| DuckDB (local) | materialize derived table; re-execute SQL | run `failed`, surfaced |

## Business Rules
- The daily total equals the sum of per-query `est_usd` for that day.
- A derived table persists and is queryable like any dataset.
- Re-run re-executes the stored `generated_sql` and must reproduce the original result.

## Success Criteria
- [ ] The daily total matches the sum of per-query costs (integration test).
- [ ] A saved derived table is queryable in a follow-up ask.
- [ ] Re-running a past query reproduces the same answer.
