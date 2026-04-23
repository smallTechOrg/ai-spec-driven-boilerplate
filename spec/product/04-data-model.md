# Data Model

## Run
| Field | Type | Notes |
|-------|------|-------|
| id | int PK | auto |
| ran_at | datetime | UTC |
| status | str | running / completed / failed |
| stale_pr_count | int | |
| error_message | str? | |
