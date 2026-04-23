# Vision

> **Project:** PR Staleness Monitor
> **Branch:** feat/test-run-1

## What This Agent Does

Queries a GitHub org for all open pull requests across every repo, identifies PRs that have been open for more than 3 days without activity, and posts a single Slack digest message listing them.

## Who Uses It

An engineering team lead or DevOps engineer who wants daily visibility into stale PRs without checking GitHub manually.

## Success Criteria

- [ ] Fetches all open PRs across all repos in a configured GitHub org
- [ ] Identifies PRs with no activity (comments or commits) in the last 3 days
- [ ] Posts one Slack message per run with a formatted list of stale PRs (repo, title, author, days open)
- [ ] Runs reliably on a daily cron schedule
- [ ] If no stale PRs exist, posts nothing (no noise)

## Out of Scope (v0.1)

- Auto-assigning or auto-closing PRs
- Per-repo configuration or filtering
- Web dashboard or API
- Email notifications
- Tracking which PRs were already notified (deduplication)

## Future Phases

- Deduplication: only notify about a PR once until it gets activity
- Per-repo or per-author filtering rules
- Web dashboard to configure thresholds and channels
- Multi-channel routing (different Slack channels per team)
