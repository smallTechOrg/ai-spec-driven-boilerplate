# Capability: Fetch Unread Emails

## What It Does
Fetches all unread emails from Gmail inbox, returns subject, sender, body snippet.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|---------|
| gmail_credentials | OAuth token | local credentials.json | yes |
| max_results | int | config (default 50) | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| emails | list[Email] | classify-draft node |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gmail API | list messages + get message | Raise; run marked failed |

## Success Criteria
- [ ] Returns list of unread emails with id, subject, sender, snippet
- [ ] Handles empty inbox (returns empty list, no error)
