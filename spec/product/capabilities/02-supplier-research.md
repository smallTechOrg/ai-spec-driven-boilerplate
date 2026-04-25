# Capability: Supplier Research

## What It Does

For each material line item in a sourcing run, the agent uses the LLM to research and generate a list of candidate suppliers with price estimates, lead times, and certification information.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|---------|
| material_name | string | MaterialLineItem | yes |
| quantity | decimal | MaterialLineItem | yes |
| unit | string | MaterialLineItem | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| supplier_candidates | list of {name, location, price_per_unit, currency, lead_time_days, certifications, notes} | AgentState → PostgreSQL |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Google Gemini (or stub) | Research prompt: find suppliers for material + quantity | Log error, continue with empty list for that material |

## Business Rules

- Generate at least 3 candidate suppliers per material (or as many as the LLM returns)
- Price per unit and lead time are estimates; must be labelled as such in the report
- Stub returns 3 hardcoded suppliers per material with distinct tags (`<node:research>`)
- If LLM returns fewer than 3 suppliers, include a note in the report

## Success Criteria

- [ ] For each material, at least 3 supplier candidates are generated (stub or real)
- [ ] Each candidate has: name, price_per_unit, lead_time_days, at least one certification or "None"
- [ ] Research node produces a list of SupplierCandidate objects (not raw text)
