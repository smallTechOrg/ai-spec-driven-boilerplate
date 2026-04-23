# Implementation Plan — PR Staleness Monitor

## Phase 1 — Domain Models + DB (DONE)
Gate: `pytest tests/unit/` — 2/2 ✅

## Phase 2 — Stubbed Pipeline (DONE)  
Gate: `pytest tests/integration/` — 3/3 ✅ (offline, zero env vars)

## Future Phases
- Phase 3: Real GitHub API (replace stub)
- Phase 4: Real Slack webhook (replace stub)
- Phase 5: APScheduler daily cron
