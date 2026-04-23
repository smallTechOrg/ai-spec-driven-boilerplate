# Vision — Email Triage Agent

## What This Agent Does
Reads unread emails from Gmail, classifies each as urgent/follow-up/ignore using Claude, drafts a reply for urgent emails, and saves all results to a local SQLite database.

## Who Uses It
A solo professional who wants to process a large inbox without reading every email manually.

## Success Criteria
- [ ] Fetches unread emails from Gmail via Google API
- [ ] Classifies each email as urgent / follow-up / ignore using Claude
- [ ] For urgent emails: generates a draft reply using Claude
- [ ] Saves classification + draft to SQLite (email_id, subject, classification, draft_reply)
- [ ] CLI invocation: `python -m emailtriage run` — processes all unread, exits

## Out of Scope (v0.1)
- Actually sending emails
- Web UI or dashboard
- Scheduling / running automatically
- Learning from user corrections

## Future Phases
- Auto-send approved drafts
- Scheduled daily runs
- Web UI to review and approve drafts
