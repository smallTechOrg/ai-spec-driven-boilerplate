# Capability: Post Slack Digest

## What It Does
Posts one Slack message listing stale PRs. Does nothing if list is empty.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|---------|
| stale_prs | list[PR] | fetch-prs | yes |
| slack_webhook_url | str | env | yes |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Slack Webhook | POST JSON | Raise; run failed |

## Success Criteria
- [ ] Empty list → no HTTP call
- [ ] Non-empty → exactly one POST, Slack returns 200
