# Capability: Recommendation Generation

## What It Does

Ranks the candidate suppliers for each material using a weighted scoring model across price, lead time, and quality certifications. Produces a structured recommendation report saved to PostgreSQL and displayed on the report page.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|---------|
| supplier_candidates | list per material | AgentState (from research node) | yes |
| scoring_weights | config | Settings (default: price 40%, lead_time 35%, certs 25%) | no |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| recommendations | list of ranked SupplierRecommendation rows | PostgreSQL |
| report_summary | text | AgentState → displayed in UI |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Google Gemini (or stub) | Summarise and justify rankings narrative | Log error, use auto-generated summary |
| PostgreSQL | INSERT SupplierRecommendation rows | Fail run with status=failed |

## Business Rules

- Scoring formula: score = (1 - normalised_price) × 0.40 + (1 - normalised_lead_time) × 0.35 + cert_score × 0.25
- cert_score = min(1.0, number_of_certifications / 3)
- Lower price → higher score; shorter lead time → higher score; more certs → higher score
- Rank 1 is the recommended supplier for each material
- Weights are configurable via env vars (WEIGHT_PRICE, WEIGHT_LEAD_TIME, WEIGHT_CERTS)

## Success Criteria

- [ ] Each material has a ranked list of recommendations in PostgreSQL after run completes
- [ ] Rank 1 supplier is the one with the highest weighted score
- [ ] Report page displays all materials with their ranked suppliers
- [ ] Run status transitions to "completed" after report is saved
