# Capability: run_observability

## What It Does
Makes every analysis transparent and accountable: shows the exact code that ran, a step timeline of the reasoning (planning → running code → checking result), per-question token usage and estimated cost, a running daily total, and (P4) streams the answer token-by-token; persists the full run history.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| run_id | string | path | for fetch |
| conversation_id | string | query (history filter) | no |
| date | string | query (daily usage) | no |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| Code panel content | code string | UI "Show code" (P1) |
| Per-question tokens + cost | numbers | UI under answer (P1); run row |
| Step timeline | ordered steps | `run_steps` (P3) → UI StepTimeline |
| Daily cost total | aggregate | `GET /usage/daily` (P4) → UI |
| Streamed answer + step events | SSE | `GET /conversations/{id}/ask/stream` (P4) |
| Run history list | rows | `GET /runs` → UI RunHistory (P4) |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| (none new) | reads persisted run/step/usage data; cost computed locally from token counts | a missing usage field defaults to 0 / "n/a"; never blocks the answer |

## Business Rules
- Token counts come from the Gemini response usage; cost is `tokens × per-token rate` for the configured model (`src/analysis/cost.py`), env-configurable rates.
- Every run is persisted with its code, result summary, tokens, cost, status, and timestamps (full run history).
- P3: each loop step is recorded as a `run_step` with its phase + code for the timeline.
- P4: the SSE stream emits step events then answer tokens then a final `done` with the full run; the daily total sums cost per calendar day.
- Observability must never leak raw rows — only code, bounded result summaries, and usage numbers.

## Success Criteria
- [ ] P1: the answer response includes the exact code and accurate token + cost numbers; the UI shows both.
- [ ] P3: a multi-step run records a `run_step` per phase and the UI timeline reflects them in order.
- [ ] P4: the SSE endpoint emits step + token + done events and the UI renders streaming + a live timeline.
- [ ] P4: `GET /usage/daily` returns a today total equal to the sum of that day's run costs.
- [ ] P4: the run-history browser lists past runs with code/result/tokens/cost/timestamps from SQLite.
