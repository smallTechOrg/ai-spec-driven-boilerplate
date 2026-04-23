# Capability: Slack Digest Notification

## What It Does

Posts a single formatted Slack message listing all stale PRs. Posts nothing if the list is empty.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|---------|
| stale_prs | list[PR] | fetch-prs capability | yes |
| slack_webhook_url | str | env | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| http_response | 200 OK | Slack API |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Slack Incoming Webhook | POST JSON payload | Log error, mark run failed |

## Business Rules

- If `stale_prs` is empty, do not post — return immediately
- Message format: header line, then one line per PR: `[repo] PR #N — title (author, X days)`
- One HTTP POST total per run (not one per PR)

## Success Criteria

- [ ] Empty list → no HTTP call made
- [ ] Non-empty list → exactly one POST to Slack webhook
- [ ] Slack returns 200 OK
