# Implementation Plan — Email Triage Agent

## Phase 1 — Domain Models + DB Schema
Gate: `pytest tests/unit/`

Files: config.py, domain/models.py, db/models.py, db/session.py, db/repository.py, tests/unit/db/

## Phase 2 — Core Agent Loop (Stubbed)
Gate: `pytest tests/integration/` — zero API calls, one Run + 3 EmailResult rows in DB

Files: agent/state.py, agent/nodes.py (stubs), agent/graph.py, agent/runner.py,
       tools/gmail.py (stub), tools/claude.py (stub), __main__.py, tests/integration/
