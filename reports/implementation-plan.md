# Implementation Plan — PR Staleness Monitor

## v0.1 Build Plan (Phases 1 + 2 only)

### Phase 1 — Domain Models + DB Schema
**Gate:** `pytest tests/unit/db/` passes; Run CRUD works; zero env vars needed

Files:
- `pyproject.toml`
- `src/prmonitor/__init__.py`
- `src/prmonitor/config.py`
- `src/prmonitor/domain/models.py` — PR, Run (Pydantic)
- `src/prmonitor/db/models.py` — DBRun (SQLAlchemy)
- `src/prmonitor/db/session.py`
- `src/prmonitor/db/repository.py` — create_run, update_run, get_runs
- `tests/unit/db/test_repository.py`
- `tests/conftest.py`

### Phase 2 — Core Agent Loop (Stubbed)
**Gate:** `pytest tests/integration/test_pipeline.py` passes; one Run row in DB with status="completed"; zero real HTTP calls

Files:
- `src/prmonitor/tools/github.py` — stub: returns 3 hardcoded stale PRs
- `src/prmonitor/tools/slack.py` — stub: prints to stdout, no HTTP call
- `src/prmonitor/agent/runner.py` — fetch → filter → notify → persist
- `src/prmonitor/__main__.py`
- `tests/integration/test_pipeline.py`

## Future Phases
- Phase 3: Real GitHub API calls
- Phase 4: Real Slack webhook
- Phase 5: APScheduler cron
- Phase 6: Deduplication (track notified PRs)
