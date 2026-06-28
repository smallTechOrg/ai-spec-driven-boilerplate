# Capability: analyze_dataset

## What It Does
Answers a natural-language question about a dataset by planning, writing pandas code, executing that code **locally** over the file (raw rows never reach the LLM), inspecting the result, and iterating within a bounded loop until it produces a prose answer with the key numbers (P4: plus chart/table).

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| dataset_id | string | path | yes |
| question | string | user (ask box) | yes |
| conversation_id | string | path (P2) | P2 |
| history | list of prior-turn summaries | server (P2, from prior runs) | P2 |
| profile | schema/profile dict | server (from `dataset_profiles`) | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| answer | prose string with key numbers | UI answer card; `messages` (assistant, P2) |
| code | pandas code string | UI "Show code" panel; `analysis_runs.code` |
| result_summary | bounded computed result | `analysis_runs.result_summary` |
| assumptions / followups | lists (P3) | UI; run row |
| viz | chart/table spec (P4) | UI Chart/PivotTable |
| tokens / cost_usd | usage | UI; run row; daily total |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini | plan, generate code, inspect (P3), finalize — sees only question + profile + result summaries | provider retry/backoff; persistent → run `failed` with surfaced error (never a fabricated answer) |
| Local sandboxed executor | run generated pandas over the dataframe(s) | code error captured (not raised) → self-correct (P3) up to step cap → honest degrade |

## Business Rules
- **Privacy spine:** no raw data rows are ever included in any Gemini prompt — only the question, the profile, and bounded result summaries. Enforced in code and asserted in tests.
- Generated code runs in a restricted namespace (whitelisted imports pandas/numpy; no `open`/`__import__`/network/fs-write); `df` (P4: `dfs`) is bound to the dataset.
- The iterate loop has a **hard step cap** (`max_steps`, default 4) — a confused agent terminates and degrades honestly.
- P1: single plan→code→execute→finalize pass (loop wired but capped to ≤1 execution). P3: real plan-then-iterate with reflection/self-correction on code errors, plus uncertainty handling (clarifying question / shown attempts / flagged best-guess).
- Honest caveat over false confidence — the agent never invents numbers it didn't compute.
- P4: generated code may emit a typed chart/table spec alongside the prose.

## Success Criteria
- [ ] A question returns a prose answer whose key numbers equal the result of the executed pandas code (asserted against a known fixture answer).
- [ ] The outbound Gemini prompt provably contains no raw data rows (asserted by inspecting the prompt in `tests/test_phase1_privacy.py`).
- [ ] The exact code that ran is returned and shown in the UI.
- [ ] P3: a question whose first code errors triggers a self-correction retry and still lands a correct answer within the step cap.
- [ ] P3: an ambiguous question yields a clarifying question or an explicitly-flagged assumption, not a confident guess.
- [ ] The tested path completes in under 30s with `gemini-2.5-flash`.
