# Architecture

## System Overview
Python process, cron-triggered. Fetches GitHub PRs → filters stale → posts Slack digest → saves run to PostgreSQL.

## Component Map
```
[Cron] → [Runner] → [GitHub API] → [filter] → [Slack Webhook]
                                                      ↓
                                              [PostgreSQL]
```

## External Dependencies
| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| GitHub REST API | Fetch repos + PRs | Fatal — mark run failed |
| Slack Incoming Webhook | Post digest | Fatal — mark run failed |
| PostgreSQL | Run history | Log error, skip — run continues |
