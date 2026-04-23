# Vision — GitHub PR Staleness Monitor

## What This Agent Does
Queries a GitHub org for open pull requests, identifies those with no activity in 3+ days, and posts a single Slack digest.

## Success Criteria
- [ ] Fetches all open PRs across all repos in a configured GitHub org
- [ ] Identifies PRs with no commits or review comments in the last 3 days
- [ ] Posts one Slack message listing stale PRs (repo, title, author, days open)
- [ ] If no stale PRs, posts nothing
- [ ] Saves each run result to PostgreSQL

## Out of Scope (v0.1)
- Auto-assigning or closing PRs
- Per-repo or per-author filtering
- Web dashboard
- Deduplication (don't re-notify same PR)

## Future Phases
- Deduplication: only notify about a PR once per week
- Configurable staleness threshold per repo
- Web dashboard for run history
