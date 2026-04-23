# Vision — Standup Bot

## What This Agent Does
Receives Slack slash command `/standup [update text]`, saves the update to PostgreSQL, and returns a confirmation. Team leads can fetch today's standups via a REST endpoint.

## Success Criteria
- [ ] POST /slack/standup saves update (user, text, timestamp) to DB and returns 200
- [ ] GET /standups?date=YYYY-MM-DD returns all updates for that day
- [ ] Slack slash command verification (signing secret) rejects invalid requests

## Out of Scope (v0.1)
- Reminders or scheduled prompts
- Formatting or summarizing standups with LLM
- Web dashboard
- Per-team filtering

## Future Phases
- Daily digest summary sent to a Slack channel
- LLM summary of all standups
- Web dashboard
