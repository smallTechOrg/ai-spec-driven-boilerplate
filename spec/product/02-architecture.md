# Architecture

## System Overview

A Python process runs on a cron schedule (via APScheduler or system cron). On each run: fetch all open PRs from GitHub API, filter for staleness, post a Slack digest via webhook.

## Component Map

```
[Cron / APScheduler]
        │
        ▼
[Agent Runner]
        │
   ┌────┴────┐
   │         │
[GitHub API] [Slack Webhook]
        │
   [PostgreSQL]
   (run history)
```

## Data Flow

1. Cron fires `run_agent()`
2. Agent fetches all repos in org via GitHub API (paginated)
3. For each repo, fetches open PRs
4. Filters: last activity > 3 days ago
5. If stale PRs found: formats and posts Slack digest
6. Saves run record to PostgreSQL (timestamp, PR count, status)

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| GitHub API | Fetch repos + PRs | Log error, mark run failed, no Slack post |
| Slack Webhook | Post digest | Log error, mark run failed |
| PostgreSQL | Run history | Log error, skip persistence — run still executes |
