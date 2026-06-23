# Capability: Visualize Result (DEFERRED — Phase 2)
## What It Does
When a result is suitable for charting, the agent proposes a small typed chart spec (type, x, y, series) from the result schema, and the UI renders it. In Phase 1 this is a clearly-labelled non-functional stub.
## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| result columns/schema | JSON | output of Ask Question | yes |
## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| chart spec | JSON (`chart` field) | `POST /ask` response → ChartView |
## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini | Propose chart spec from result schema (not raw rows beyond cap) | omit chart, log |
## Business Rules
- Chart proposal uses the result schema + capped preview only — token economy preserved.
## Success Criteria
- [ ] An aggregation result renders a chart matching the data (Phase 2).
- [ ] Phase 1: the Charts card is a visible, labelled "Coming soon" stub, not interactive.
