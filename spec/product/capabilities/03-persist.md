# Capability: Persist Results

## What It Does
Saves each classified email result to SQLite.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|---------|
| result | EmailResult | classify-draft node | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| saved record | EmailResult row | SQLite |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | INSERT email_results | Log error, continue |

## Success Criteria
- [ ] Each processed email has one row in email_results
- [ ] Row contains: email_id, subject, sender, classification, draft_reply, processed_at
