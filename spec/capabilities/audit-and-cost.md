# Capability: Audit & Cost Tracking

## What It Does
Records every ask to a persistent audit history (question, plan, generated SQL, result summary, token counts, estimated USD cost, timestamps) and exposes per-query cost in the answer and a retrievable run history.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| run result | the finalized AgentState | the graph runner | yes |
| token usage | prompt/completion tokens per LLM call | Gemini response metadata | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| Run audit record | row (question, plan_json, generated_sql, result_summary_json, tokens, est_usd, timestamps) | SQLite `runs` |
| per-query cost | {prompt_tokens, completion_tokens, est_usd} | `/api/ask` response |
| run history | list of runs (most recent first) | `GET /api/runs` |
| single run detail | full audit record | `GET /api/runs/{id}` |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite (SQLAlchemy) | insert/update the Run row | run still returns; persistence error logged + surfaced |

## Business Rules
- Every ask (success or failure) writes a Run row; failures store the attempted SQL and error.
- `est_usd` is computed from real token counts × a configurable flash price-per-1K-tokens constant.
- `result_summary_json` stores aggregates + narration only — never a raw-row dump (privacy boundary extends to persistence).
- The daily-total rollup is deferred to Phase 5; Phase 1 shows per-query cost only.

## Success Criteria
- [ ] After an ask, `GET /api/runs` lists the run with its question, generated_sql, est_usd, and timestamp.
- [ ] `GET /api/runs/{id}` returns the full record including plan, SQL, result summary, and token counts.
- [ ] `est_usd` and token counts are non-zero and reflect the real Gemini call.
- [ ] A failed run is recorded with status `failed`, the attempted SQL, and the error message.
