# BlogForge — Autonomous Blog Generation Agent

BlogForge generates full blog posts (text + cover images) on a schedule, with no manual writing required. Configure your blog identity and writer personas once; the agent picks topics, writes posts, and stores them in a content library you can browse in a web dashboard.

---

## What It Does

1. **Discovers topics** — searches DuckDuckGo + Tavily for niche-relevant trending content, merges with Gemini-brainstormed ideas, deduplicates against all previously used topics
2. **Generates posts** — each post is written by an assigned writer persona using Gemini Flash (800–1500 words, structured Markdown, unique slug)
3. **Generates cover images** — Gemini Imagen produces a 1200×630 cover image per post, saved to `./images/`; SVG placeholder used as fallback
4. **Stores in a content library** — all posts and metadata persist in a local SQLite database
5. **Serves a dashboard** — FastAPI web UI to configure settings, manage writers, trigger runs, and browse posts
6. **Runs on a schedule** — APScheduler fires generation runs at a configured cron interval

---

## Current Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Domain models + SQLite schema | ✅ Complete (21/21 tests) |
| 2 | Core agent loop (stubbed) | ✅ Complete (5/5 tests) |
| 3 | Real Gemini text generation | Pending |
| 4 | Real Gemini Imagen cover images | Pending |
| 5 | Topic discovery (DuckDuckGo + Tavily + Gemini) | Pending |
| 6 | APScheduler cron scheduling | Pending |
| 7 | Web dashboard (4 tabs) | Pending |
| 8 | Integration tests | Pending |
| 9 | Observability + polish | Pending |

---

## Setup

### Requirements

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) for dependency management
- A Google Gemini API key (text + Imagen access)
- A Tavily API key (optional — topic discovery degrades gracefully without it)

### Install

```bash
git clone https://github.com/smallTechOrg/ai-spec-driven-boilerplate.git blogforge
cd blogforge
git checkout feat/blog-generator
uv sync
cp .env.example .env
# edit .env — set GEMINI_API_KEY and optionally TAVILY_API_KEY
```

### Run

```bash
python -m blogforge serve
# or: blogforge serve (after uv install)
```

Dashboard available at `http://localhost:8000`.

### Test

```bash
python -m pytest
```

---

## Configuration

All configuration is via environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | required | Google Gemini API key |
| `TAVILY_API_KEY` | optional | Tavily search API key |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/blogforge.db` | SQLite database path |
| `IMAGES_DIR` | `./images` | Cover image storage directory |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |

---

## Architecture

```
[Dashboard UI]  ←HTTP→  [FastAPI Server]
                              │
                    ┌─────────┴────────────┐
                    │                      │
             [APScheduler]         [LangGraph Agent]
             (cron triggers)               │
                    │        ┌─────────────┴──────────────┐
                    └────────►                            │
                             [SQLite DB]         [External APIs]
                             (content library)   ┌──────────────────┐
                                       │         │ Gemini Flash     │
                                  [./images/]    │ Gemini Imagen    │
                                  (cover imgs)   │ DuckDuckGo       │
                                                 │ Tavily           │
                                                 └──────────────────┘
```

**Agent pipeline (LangGraph):**
```
topic_discovery → writer_assignment → post_generation → image_generation → finalize
       ↓error                ↓error
   handle_error          handle_error
```

---

## Project Layout

```
src/blogforge/
  agent/          ← LangGraph state, nodes, graph, runner
  tools/          ← topic_discovery, post_generation, image_generation
  db/             ← SQLAlchemy models, session, repository
  domain/         ← Pydantic domain models
  api/            ← FastAPI routes (Phase 7)
  dashboard/      ← HTML/CSS/JS dashboard (Phase 7)
  config.py       ← Settings via pydantic-settings
  main.py         ← FastAPI app factory
spec/
  product/        ← Vision, architecture, capabilities, data model, API, UI, agent graph
  engineering/    ← Tech stack, code style, phases, AI agent rules
tests/
  unit/           ← Unit tests per module
  integration/    ← End-to-end pipeline tests
```

---

## Spec

Full spec lives in `spec/product/`. Key files:

- [Vision](spec/product/01-vision.md) — what it does, success criteria, out of scope
- [Architecture](spec/product/02-architecture.md) — component map and data flow
- [Agent Graph](spec/product/07-agent-graph.md) — LangGraph state, nodes, edge topology
- [Data Model](spec/product/04-data-model.md) — entities and relationships
- [Capabilities](spec/product/capabilities/) — one file per feature

This branch is built on the [ai-spec-driven-boilerplate](https://github.com/smallTechOrg/ai-spec-driven-boilerplate) — see `main` for the template.
