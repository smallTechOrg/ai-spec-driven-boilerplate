# Vision

## What This Agent Does

The UP Police AI Workshop is a learning progress tracker and self-assessment tool for Uttar Pradesh Police staff. Officers self-register with their name and badge number, complete a 20-question self-assessment across four capability areas (AI Tools, Cybersecurity, Communication & Data Analytics, CCTV & Surveillance AI), and receive an auto-generated personalised 30-day learning plan with daily tasks and resource links. Officers track their progress through the plan marking days as Done, In Progress, or Not Started.

## Who Uses It

Uttar Pradesh Police officers and staff at all levels. Users may have little to no prior AI experience. They want structured, self-paced learning that builds practical AI literacy relevant to their work.

## Core Problem Being Solved

UP Police staff need to build AI literacy quickly and practically. There is no structured, accessible, self-paced learning path calibrated to individual skill levels. This tool replaces ad-hoc training by providing a personalised, trackable 30-day plan based on each officer's self-assessed starting point.

## Success Criteria

- [ ] An officer can self-register in under 1 minute with no password required
- [ ] The 20-question assessment completes in under 5 minutes and generates a personalised plan instantly
- [ ] The 30-day plan contains appropriate-level tasks for each of 4 capability areas
- [ ] Progress can be tracked day by day with a visual progress bar
- [ ] The app works entirely offline-capable (no external CSS/JS CDN dependencies)

## What This Agent Does NOT Do (Out of Scope)

- No LLM or AI calls in v0.1 — plan generation is rule-based
- No password authentication — badge number is the identifier
- No admin dashboard or reporting in v0.1
- No email notifications or reminders
- No multi-language support in v0.1

## Key Constraints

- Port 8001 (hard-coded)
- Cookie-based sessions only (no JWT, no OAuth)
- PostgreSQL only (no SQLite, no in-memory DB)
- Self-contained: no external CSS/JS frameworks (works offline)

## Phases of Development

| Phase | Description | Success Gate |
|-------|-------------|--------------|
| 1 | Domain models, database schema, plan generation logic | All unit tests pass; alembic upgrade head succeeds |
| 2 | Web UI (FastAPI + Jinja2), full golden-path integration test, live server responding | All integration tests pass; curl /health and / return 200 |
