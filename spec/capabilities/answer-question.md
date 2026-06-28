# Capability: Answer a Question (Plan-Then-Execute, Privacy Boundary)

## What It Does
Turns a plain-English question over a loaded dataset into a rich answer (plain-language answer + key-stat callouts + auto-selected chart + summary table + written insight + suggested follow-ups) by drafting a plan, running DuckDB SQL **locally**, and narrating only the aggregate results — raw rows never leave the machine.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| dataset_id | string (uuid) | client (`POST /api/ask`) | yes |
| question | string (plain English) | client | yes |
| schema + profile | column metadata | cached on the dataset | yes (loaded internally) |
| messages | prior conversation turns | SQLite (threaded into the plan prompt) | no |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| answer | plain-language string | API response (rich-answer envelope) |
| key_stats | list of {label, value, unit?} | API response |
| chart_spec | declarative chart {type, x, y, data} | API response |
| summary_table | {columns, rows} (aggregated, capped) | API response |
| insight | written interpretation string | API response |
| follow_ups | 2–3 suggested questions | API response |
| plan_steps + generated_sql | the plan + exact SQL that ran | API response (code/steps panel) |
| cost | {prompt_tokens, completion_tokens, est_usd} | API response |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini (`gemini-2.5-flash`) | draft plan + SQL; narrate aggregates; suggest follow-ups — **schema + aggregates only** | retry/backoff → run status `failed`, attempted SQL surfaced |
| DuckDB (local) | run the generated SQL locally | run status `failed`, attempted SQL surfaced |

## Business Rules
- **Privacy boundary (non-negotiable):** the only data sent to Gemini is schema (column names/types), the profile, and the aggregate results. Raw data rows are NEVER placed in any prompt. (Enforced structurally in the graph; see [agent.md](../agent.md).)
- Generated SQL is read-only (`SELECT`); the execute node rejects DDL/DML.
- A typical answer returns in under ~30 seconds locally.
- On any failure the agent always shows what it tried (plan + attempted SQL) — never a silent or fabricated answer.
- The chart type is auto-selected by the narrate node from the aggregate shape.

## Success Criteria
- [ ] Asking "What were total sales by region?" of the sample dataset returns a non-empty answer, ≥1 key stat, a chart_spec, a summary_table, and an insight, with the correct top region.
- [ ] The response includes the exact `generated_sql` and `plan_steps`.
- [ ] **Privacy test (gate):** with a dataset containing distinctive sentinel raw-row values, a real end-to-end ask captures every prompt sent to Gemini and asserts no sentinel value appears in any prompt, while `query_rows` is non-empty (data was queried locally). The fixture is large enough that a sampled answer differs from the full-data answer.
- [ ] A question yielding bad SQL returns `status: "failed"` with the attempted SQL surfaced, not a crash.
- [ ] `cost` reflects real token counts from the Gemini response (not zero, not hard-coded).
