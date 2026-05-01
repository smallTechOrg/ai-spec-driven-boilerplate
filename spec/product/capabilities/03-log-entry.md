# Capability: Log Entry

## What It Does

Persists a completed food analysis result to PostgreSQL as a `FoodLog` record, and returns the new row's ID to the pipeline.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|---------|
| food_name | str | Pipeline state | yes |
| calories_kcal | float | Pipeline state | yes |
| protein_g | float | Pipeline state | yes |
| carbs_g | float | Pipeline state | yes |
| fat_g | float | Pipeline state | yes |
| provider | str | Pipeline state | yes |
| image_filename | str | Pipeline state | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| run_id | int | Pipeline state (`FoodState.run_id`) |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| PostgreSQL | `INSERT INTO food_logs` | Set `FoodState.error`, return HTTP 500 to user |

## Business Rules

- `analyzed_at` is set to the current UTC time by the server — never trusted from the client
- Partial records are never written: if any required field is missing, raise immediately
- Records are never updated or deleted in v0.1

## Success Criteria

- [ ] A complete pipeline run creates exactly one row in `food_logs`
- [ ] `analyzed_at` is set to a UTC timestamp
- [ ] A DB connection failure surfaces as HTTP 500 (not a silent discard)
