# Capability: Fetch Stale PRs

## What It Does

Fetches all open pull requests across every repository in a GitHub org and returns those with no activity in the last N days.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|---------|
| github_org | str | config/env | yes |
| github_token | str | env | yes |
| stale_days | int | config (default: 3) | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| stale_prs | list[PR] | Slack notifier |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| GitHub REST API | GET /orgs/{org}/repos, GET /repos/{owner}/{repo}/pulls | Raise exception; run marked failed |

## Business Rules

- Only open PRs are considered
- "No activity" = no commits or review comments since `now - stale_days`
- If a repo has no open PRs, skip silently

## Success Criteria

- [ ] Returns all open PRs with last-activity timestamp
- [ ] Correctly filters out PRs with recent activity
- [ ] Handles GitHub pagination (> 30 repos or > 30 PRs per repo)
