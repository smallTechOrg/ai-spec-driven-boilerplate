# Capability: Fetch Stale PRs

## What It Does
Fetches all open PRs from every repo in a GitHub org and returns those with no activity for N days.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|---------|
| github_org | str | env | yes |
| github_token | str | env | yes |
| stale_days | int | config (default 3) | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| stale_prs | list[PR] | slack-digest |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| GitHub REST API | GET /orgs/{org}/repos, GET /repos/.../pulls | Raise; run failed |

## Success Criteria
- [ ] Returns PRs with no activity since `now - stale_days`
- [ ] Handles pagination for orgs with >30 repos
- [ ] Empty result is valid (returns [])
