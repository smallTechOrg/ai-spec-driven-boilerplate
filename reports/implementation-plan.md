# Implementation Plan — BlogForge

**Status:** Approved (plan-reviewer + user)  
**Date approved:** 2026-04-23  
**Branch:** feat/blog-generator

---

## Minimal Working Thing (Phase 2 Goal)

By the end of Phase 2, `POST /runs/trigger` accepts a manual trigger and runs the full 4-node LangGraph pipeline (topic_discovery → writer_assignment → post_generation → image_generation) end-to-end with zero external API calls. Hardcoded topic, mocked Gemini text response, SVG placeholder image. Post persisted to SQLite with all fields. Run transitions to "completed" and is queryable via `GET /runs/{id}`.

---

## Phases

### Phase 1 — Domain Models + SQLite Schema
**Goal:** All Pydantic models, SQLAlchemy ORM models, Alembic migrations, and CRUD repository.

**Files:**
- `src/blogforge/__init__.py`
- `src/blogforge/config.py`
- `src/blogforge/domain/models.py`
- `src/blogforge/db/models.py`
- `src/blogforge/db/session.py`
- `alembic/` + `alembic/versions/001_initial_schema.py`
- `src/blogforge/db/repository.py`
- `tests/conftest.py`
- `tests/unit/db/test_repository.py`

**Gate:** `pytest tests/unit/db/test_repository.py` — all CRUD ops pass, Pydantic models returned correctly.

---

### Phase 2 — Core Agent Loop (Stubbed) ← ARCHITECTURAL SPIKE
**Goal:** 4-node LangGraph pipeline runs end-to-end with all external calls stubbed. One post saved to DB. Zero network calls.

**Files:**
- `src/blogforge/agent/state.py`
- `src/blogforge/agent/nodes.py` (4 stub nodes)
- `src/blogforge/agent/graph.py`
- `src/blogforge/agent/runner.py`
- `src/blogforge/tools/topic_discovery.py` (stub — hardcoded topics)
- `src/blogforge/tools/post_generation.py` (stub — hardcoded Markdown)
- `src/blogforge/tools/image_generation.py` (stub — SVG placeholder)
- `src/blogforge/main.py`
- `src/blogforge/__main__.py`
- `tests/unit/agent/test_nodes.py`
- `tests/integration/test_agent_pipeline.py`

**Gate:** `pytest tests/integration/test_agent_pipeline.py::test_agent_runs_end_to_end_with_stubs` — post in DB, all fields populated, run status "completed", zero external API calls.

---

### Phase 3 — Real Post Generation (Gemini Text)
**Goal:** Replace stub with real Gemini `gemini-2.0-flash` call. Retry on failure. Mark failed posts, continue run.

**Files:**
- `src/blogforge/config.py` (add `GEMINI_API_KEY`)
- `src/blogforge/tools/post_generation.py` (real Gemini call)
- `src/blogforge/agent/nodes.py` (error handling)
- `src/blogforge/db/models.py` (add `status` column to DBPost)
- `src/blogforge/db/repository.py` (update)
- `tests/unit/tools/test_post_generation.py`
- `tests/integration/test_agent_pipeline.py` (update)

**Gate:** `pytest tests/integration/test_agent_pipeline.py::test_agent_generates_valid_post_with_real_gemini` — post has 3+ `##` headings, 600–2000 words.

---

### Phase 4 — Image Generation (Gemini Imagen + SVG Fallback)
**Goal:** Real Imagen API call saves PNG to `./images/`. On failure, SVG placeholder saved instead. Async file I/O via `aiofiles`.

**Files:**
- `src/blogforge/tools/image_generation.py` (real Imagen + aiofiles + SVG fallback)
- `src/blogforge/agent/nodes.py` (update)
- `tests/unit/tools/test_image_generation.py`
- `tests/integration/test_agent_pipeline.py` (update)

**Gate:** `pytest tests/integration/test_agent_pipeline.py::test_agent_saves_cover_image` — file exists at `cover_image_path`, PNG or SVG.

---

### Phase 5 — Topic Discovery (DuckDuckGo + Tavily + Gemini)
**Goal:** DuckDuckGo + Tavily searched in parallel, merged and deduplicated. Gemini selects final topics. Filtered against UsedTopic history.

**Files:**
- `src/blogforge/config.py` (add `TAVILY_API_KEY`)
- `src/blogforge/tools/topic_discovery.py` (DDG + Tavily + Gemini + dedup)
- `src/blogforge/agent/nodes.py` (update)
- `tests/unit/tools/test_topic_discovery.py`
- `tests/integration/test_agent_pipeline.py` (update)

**Gate:** `pytest tests/unit/tools/test_topic_discovery.py tests/integration/test_agent_pipeline.py` — 3+ unique topics per run, no repeats across consecutive runs.

---

### Phase 6 — Writer Assignment
**Goal:** Round-robin assignment of topics to active writers. ValueError on empty writer list.

**Files:**
- `src/blogforge/tools/writer_assignment.py`
- `src/blogforge/agent/nodes.py` (update)
- `tests/unit/tools/test_writer_assignment.py`

**Gate:** `pytest tests/unit/tools/test_writer_assignment.py` — deterministic round-robin, ValueError on empty.

---

### Phase 7 — FastAPI Routes
**Goal:** All REST API endpoints: blog config, writers, runs, posts.

**Files:**
- `src/blogforge/api/blog.py`
- `src/blogforge/api/writers.py`
- `src/blogforge/api/runs.py`
- `src/blogforge/api/posts.py`
- `src/blogforge/api/schemas.py`
- `src/blogforge/main.py` (register routers)
- `tests/unit/api/test_*.py`
- `tests/integration/test_api.py`

**Gate:** `pytest tests/integration/test_api.py` — all endpoints correct status/shapes; trigger returns run_id.

---

### Phase 8 — Dashboard UI (4 tabs)
**Goal:** Self-contained `index.html` with Settings, Writers, Generate, and Library tabs. Vanilla JS fetch().

**Files:**
- `src/blogforge/dashboard/index.html`
- `src/blogforge/main.py` (serve dashboard)

**Gate:** Manual browser test — all 4 tabs load; Settings saves; Writers CRUD works; Generate triggers run; Library shows posts.

---

### Phase 9 — APScheduler (Cron Scheduling)
**Goal:** Cron-based automatic runs. Hot-swap on config update. Prevent concurrent runs.

**Files:**
- `src/blogforge/scheduler.py`
- `src/blogforge/main.py` (startup/shutdown)
- `src/blogforge/api/blog.py` (cron validation + scheduler update)
- `tests/unit/scheduler/test_scheduler.py`

**Gate:** `pytest tests/unit/scheduler/test_scheduler.py` — cron fires at expected time, invalid cron rejected with 422.

---

### Phase 10 — Observability + Logging
**Goal:** Structured logging throughout. API error handlers. Dashboard error states.

**Files:**
- `src/blogforge/logging.py`
- All source files (logging statements)
- `src/blogforge/api/` (exception handlers)
- `src/blogforge/dashboard/index.html` (error banner)
- `tests/integration/test_observability.py`

**Gate:** `pytest tests/integration/test_observability.py` — all major ops produce log entries; failed run shows in API.

---

### Phase 11 — Integration Tests + Edge Cases
**Goal:** Full pipeline test, all documented failure modes, concurrent access safety.

**Files:**
- `tests/integration/test_full_pipeline.py`
- `tests/integration/test_failure_modes.py`
- `tests/integration/test_concurrent_access.py`

**Gate:** `pytest tests/integration/` — all failure modes handled gracefully; no crashes on bad input.

---

### Phase 12 — Polish + Documentation
**Goal:** README, code review, mypy, final drift check.

**Files:**
- `README.md`
- Code review across all src files
- `spec/` drift verification

**Gate:** README user-accepted; `pytest` 80%+ coverage; `mypy --strict` passes.

---

## Deferred

- Phase 13+: Static HTML export (site rendering)
- SEO, social, multi-blog, video: out of scope

---

## Current Status

| Phase | Status |
|-------|--------|
| 1 | 🔲 Not started |
| 2–12 | 🔲 Not started |
