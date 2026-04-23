# Data Model

## Entities

### Run
Tracks each execution of the agent.

| Field | Type | Notes |
|-------|------|-------|
| id | int PK | auto |
| ran_at | datetime | UTC, when the run started |
| status | str | "completed" / "failed" |
| stale_pr_count | int | number of stale PRs found |
| error_message | str? | set if status is "failed" |

No other entities for v0.1 — PRs are not persisted.
