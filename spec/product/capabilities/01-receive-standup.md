# Capability: Receive Standup

## What It Does
Handles POST /slack/standup, verifies Slack signature, saves update to DB.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|---------|
| user_id | string | Slack payload | yes |
| username | string | Slack payload | yes |
| text | string | Slack payload | yes |
| slack_signature | string | HTTP header | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| response | {text: string} | Slack (200 JSON) |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| PostgreSQL | INSERT standup | Return 500 |

## Success Criteria
- [ ] Valid request → saved to DB, returns 200 with confirmation text
- [ ] Invalid signature → returns 401, nothing saved
