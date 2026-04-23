# Capability: Classify and Draft

## What It Does
For each email: classifies as urgent/follow-up/ignore using Claude. For urgent emails, generates a draft reply.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|---------|
| email | Email | fetch node | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| classification | "urgent" / "follow-up" / "ignore" | persist node |
| draft_reply | str or None | persist node |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Claude API | classify (1 call), draft reply if urgent (1 call) | Mark email as failed, continue |

## Business Rules
- Classification and draft are separate LLM calls
- Non-urgent emails get draft_reply = None
- Failed emails are saved with classification = "error"

## Success Criteria
- [ ] Each email gets a classification in {urgent, follow-up, ignore, error}
- [ ] Urgent emails get a non-empty draft_reply
- [ ] One email failing does not stop others from processing
