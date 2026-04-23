# Capability: Scheduling

## What It Does

Fires automatic generation runs on a user-configured cron schedule using an embedded APScheduler instance.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|---------|
| schedule_cron | str | Blog config | yes (if scheduling is active) |

## Outputs

None directly — triggers a generation run (same as `POST /runs/trigger` with `trigger = "scheduled"`).

## External Calls

None. APScheduler is embedded in the same process.

## Business Rules

- If `blog.schedule_cron` is null or empty, no scheduled job is registered
- When `blog.schedule_cron` is updated via the dashboard, the scheduler is reconfigured immediately (old job removed, new job registered)
- If a scheduled run fires while a run is already in progress, the scheduled run is skipped (logged as "skipped — run in progress")
- The scheduler uses the server's local timezone. Cron expression format: standard 5-field cron (`* * * * *`)
- On server startup, the scheduler is initialised from the current `blog.schedule_cron` value in the DB
- Valid cron examples: `"0 8 * * 1"` (every Monday 8am), `"0 9 * * *"` (daily 9am)

## Success Criteria

- [ ] A cron expression saved in blog settings causes a run to fire at the expected time
- [ ] Updating the cron expression immediately updates the schedule (no restart required)
- [ ] Setting cron to null/empty cancels the schedule
- [ ] A scheduled run that fires during an active run is skipped and logged
- [ ] Invalid cron expression is rejected with a 422 error at the API layer (before saving)
