# Capability: Answer Question with Computed pandas

## What It Does
Translates the user's natural-language question into a pandas computation via the LLM, then executes that computation locally over the full dataset in a constrained sandbox to produce the actual answer and the auditable code.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| schema | list of {name, dtype} | `profile_csv` | yes |
| sample_rows | list of row dicts (capped) | `profile_csv` | yes |
| question | string | `POST /runs` body | yes |
| full DataFrame | pandas.DataFrame | `profile_csv` (local) | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| generated_code | string (pandas snippet assigning `result`) | AgentState + `RunRow.generated_code` |
| result_table | {columns, rows} or scalar wrapper | AgentState + `RunRow.result_table` |
| truncated | bool | AgentState (Phase 2) |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini (`gemini-2.5-flash`) | Generate the pandas snippet from schema + sample + question (NOT full data) | set `error` → `handle_error` |
| Local sandbox (`src/analysis/sandbox.py`) | Execute the snippet over the full `df` | set categorized `error`; Phase 2 retries `generate_code` once |

## Business Rules
- Only schema + capped sample + question are sent to Gemini — never the full dataset (constraint 1).
- The generated snippet must assign its answer to `result` using the bound name `df`; it is statically validated (no imports, no dunders, no `os`/`sys`/`open`) and run under a timeout and result-size cap (see [`architecture.md` → Sandbox Security Model](../architecture.md#sandbox-security-model)).
- The exact generated code is preserved and returned (constraint 2 — show its work), even on failure where possible.
- The four core analytical shapes must work: group-by aggregation, filter + aggregate, sort + top-N, single-value aggregate.

## Success Criteria
- [ ] "Total sales by region" returns a correct grouped sum table whose values match a hand-computed check on the fixture.
- [ ] A filter + aggregate (e.g. "total sales where region = 'North'") returns the correct scalar/row.
- [ ] A sort + top-N (e.g. "top 3 products by revenue") returns exactly N correctly-ordered rows.
- [ ] A single-value aggregate (e.g. "how many orders are there") returns the correct count.
- [ ] `generated_code` in the response is the exact snippet that ran.
- [ ] A snippet containing `import`, a dunder, or file/network access is rejected and never executed.
