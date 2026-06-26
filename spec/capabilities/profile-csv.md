# Capability: Profile Uploaded CSV

## What It Does
Parses the uploaded CSV locally and builds the minimal context the LLM may see — the column schema and a capped sample of rows — while keeping the full dataset on-machine.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| csv_text | string | `POST /runs` body | yes |
| question | string | `POST /runs` body | yes (carried through; not used by this step) |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| schema | list of {name, dtype} | AgentState (LLM-visible) |
| sample_rows | list of row dicts (≤ AGENT_SAMPLE_ROWS, hard cap 20) | AgentState (LLM-visible) |
| row_count | int | AgentState |
| full DataFrame | pandas.DataFrame | AgentState (local only — never sent to LLM) |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| pandas (local) | `read_csv` parse + dtype inference | set `error` → `handle_error` (no LLM, no network) |

## Business Rules
- Reject empty input, unparseable CSV, files over `AGENT_MAX_UPLOAD_BYTES` (5 MB), or over `AGENT_MAX_ROWS` (200k) — with a clear message.
- The sample is capped at `AGENT_SAMPLE_ROWS` (default 15, hard cap 20). Only schema + sample + question may reach the LLM (constraint 1).
- The full DataFrame is retained in memory for local execution and is never serialized into any prompt or persisted as a dataset.

## Success Criteria
- [ ] A valid CSV yields a schema listing every column with an inferred dtype.
- [ ] `sample_rows` length ≤ the configured cap (and ≤ row_count).
- [ ] A non-CSV / malformed upload sets a clear `error` and routes to `handle_error` without crashing.
- [ ] No prompt produced downstream contains more rows than the capped sample (verifiable from the prompt payload).
