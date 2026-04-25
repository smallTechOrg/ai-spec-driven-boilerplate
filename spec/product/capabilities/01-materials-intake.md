# Capability: Materials Intake

## What It Does

Accepts a project name and a list of materials (name, quantity, unit) from the user via a web form, validates the input, and creates a SourcingRun record in the database.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|---------|
| project_name | string | Web form | yes |
| materials | list of {name, quantity, unit} | Web form | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| sourcing_run_id | UUID | PostgreSQL + HTTP redirect |
| run_status | enum(pending, running, completed, failed) | PostgreSQL |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| PostgreSQL | INSERT SourcingRun + MaterialLineItem rows | Return 500, show error page |

## Business Rules

- Project name must be non-empty and ≤ 200 characters
- Materials list must contain at least 1 item
- Quantity must be a positive number
- Unit must be a non-empty string (e.g., "tonnes", "bags", "m²")
- On successful creation, immediately enqueue the sourcing run (trigger the agent)

## Success Criteria

- [ ] Submitting a valid form creates a SourcingRun and MaterialLineItem rows in PostgreSQL
- [ ] Submitting an invalid form returns the form with validation errors
- [ ] The user is redirected to a run-status page after successful submission
