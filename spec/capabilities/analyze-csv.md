# Capability: Analyze Uploaded CSV

## What It Does
Takes one locally-uploaded CSV and one natural-language question, computes the real answer over
the full local data via locally-executed pandas code, and returns the numeric answer, a short
plain-language explanation, and the exact code that produced it.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| dataset_id | string | path param (from a prior `POST /datasets` upload) | yes |
| question | string | request body of `POST /datasets/{id}/ask` | yes |
| (derived) schema | list[{name,dtype}] | computed locally from the uploaded file | yes |
| (derived) sample/summary | object | first N rows + per-column stats, computed locally | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| answer | string (numeric, human-readable) | `/ask` response + `QueryRow.result_json` |
| explanation | string | `/ask` response + `QueryRow.explanation` |
| code | string (the executed pandas) | `/ask` response + `QueryRow.code` |
| result | JSON value | `/ask` response + `QueryRow.result_json` |
| observability | structured logs | `src/observability/events.py` |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini (LLM) | propose pandas code from schema+sample+question | timeout/try-except → human-readable error, `status=failed` |
| Gemini (LLM) | explain the numeric result | timeout/try-except → human-readable error, `status=failed` |
| Local sandbox | execute proposed code over the full local DataFrame | structured error → one repair retry → then graceful failure |
| Local filesystem | read `data/uploads/<id>.csv` | missing/corrupt → human-readable error |

> No external call ever receives the full dataset — only schema + bounded sample (propose) and
> the numeric result (explain). See `spec/agent.md` → data-locality contract.

## Business Rules
- The full dataset never leaves the local machine; only schema + bounded sample/summary go to
  the LLM for code proposal, and only the numeric result goes to the LLM for explanation.
- Every successful answer returns all three of: numeric answer, explanation, and executed code.
- The returned `code`, re-run against the same uploaded file, must reproduce the same `result`.
- Proposed code executes only in the restricted local sandbox (`df`, `pd`, safe builtins;
  wall-clock timeout); code that errors gets exactly one auto-repair attempt before a graceful
  failure.
- One file, one single-turn question in Phase 1 (multi-turn, Excel, charts, multi-file, DB are
  later phases / labelled stubs).

## Gate questions the test MUST exercise (hard/idiomatic)
Run against the real Gemini key + real SQLite, over `tests/fixtures/sales.csv`
(`region, amount, units, date` with at least one messy column, e.g. ` Amount ` with stray
whitespace or mixed casing, and some null cells):

1. **Aggregation:** "What is the total amount?" → matches `df['amount'].sum()` within tolerance.
2. **Group-by + ranking:** "Which region has the highest average amount?" → matches
   `df.groupby('region')['amount'].mean().idxmax()`.
3. **Filtering + count:** "How many rows have units greater than 10?" → matches
   `(df['units'] > 10).sum()`.
4. **Correlation:** "What is the correlation between amount and units?" → matches
   `df['amount'].corr(df['units'])` within tolerance.
5. **Messy column:** a question referencing a column whose header has stray
   whitespace/casing/nulls → the agent still resolves the right column and returns the correct
   number (proves robustness to real-world headers).

## Validation the answer must pass
- Response contains non-empty `answer`, `explanation`, and `code`.
- `code` is a string containing pandas referencing `df` and assigning `result`.
- The numeric `result` equals the hand-computed pandas result within floating-point tolerance
  (`abs(got - expected) <= 1e-6 * max(1, abs(expected))`).
- Re-executing the returned `code` against the same fixture reproduces the same `result`.
- The captured LLM request for `propose_code` contains the schema + bounded sample but NOT the
  full row set (assert payload row count <= `sample_rows`).

## Success Criteria
- [ ] All five gate questions return correct numbers within tolerance.
- [ ] Every response carries answer + explanation + code.
- [ ] Re-running returned code reproduces the number for each gate question.
- [ ] The propose-code LLM payload contains at most `sample_rows` data rows (no full-data egress).
- [ ] A malformed CSV, an empty question, and code that errors past the repair budget each yield
      a human-readable error and `status=failed` (no crash, no stack trace).
