# Capability: Cross-Dataset Query & Dashboards (DEFERRED — Phase 4)
## What It Does
Answers one NL question that spans multiple datasets (DuckDB joins across registered tables) and lets the user pin results/charts into a persistent dashboard. Phase 1 ships both as clearly-labelled non-functional stubs.
## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| dataset_ids | list[string] | `POST /ask` (multi-select) | yes |
| question | string | `POST /ask` | yes |
| pin request | JSON | `POST /dashboards` (Phase 4) | no |
## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| joined result + narrative | JSON | Result view |
| Dashboard / DashboardItem | metadata rows | SQLite (Phase 4) |
## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini | Multi-table SQL generation (still under sample cap) | 400/502 |
| DuckDB | Execute join across dataset tables | 400/500 |
## Business Rules
- Multi-table prompts still respect `AGENT_MAX_SAMPLE_ROWS` per table.
## Success Criteria
- [ ] A question joining two datasets returns a correct joined result (Phase 4).
- [ ] Pinned dashboard items persist across restart (Phase 4).
- [ ] Phase 1: Dashboards and Cross-Dataset Query cards are visible, labelled "Coming soon" stubs.
