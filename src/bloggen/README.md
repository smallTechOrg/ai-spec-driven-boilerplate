# BlogGen

AI-powered blog writing assistant. Define your writing voice, create AI writer personas, and generate article drafts using Google Gemini.

> **Before you run anything:** `cd` into `src/bloggen/` first. Every command (`uv sync`, `uv run alembic`, `uv run pytest`, `uv run python`) must be run from this directory — the one containing `pyproject.toml`. Running from the repo root will fail.

## Features (v0.1)

- **Voice definition** — save your personal writing tone and style
- **Writer personas** — create named AI writers with distinct styles (e.g. "The Academic", "The Storyteller")
- **Article generation** — generate a full blog draft from a topic using LangGraph + Gemini
- **Review loop** — request revisions, approve, or reject drafts via the web UI

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (`pip install uv` or `brew install uv`)
- PostgreSQL 15+ (for real use) OR SQLite (for stub/dev mode)
- Google Gemini API key (for real generation; optional for stub mode)

## Setup

```bash
# Run ALL commands from src/bloggen/ (where pyproject.toml lives)
cd path/to/repo/src/bloggen

uv sync
cp .env.example .env
# Edit .env — set BLOGGEN_DATABASE_URL to your PostgreSQL connection string
# e.g. postgresql+psycopg2://youruser:@localhost:5432/bloggen

uv run alembic upgrade head    # creates all tables in PostgreSQL
uv run alembic current         # must print a revision hash — blank = failed
```

## Run (local)

```bash
uv run python -m bloggen
# Open http://localhost:8001
```

The web UI is served at `http://localhost:8001`. Use it to:
1. Create a voice (Voices tab)
2. Create writer personas (Writers tab)
3. Generate articles (Article Generator tab)

## Run in stub mode (no Gemini API key needed)

Leave `BLOGGEN_GEMINI_API_KEY` empty in `.env`. Articles will be generated with a placeholder stub draft instead of real LLM output. The full pipeline still runs — agent graph, DB writes, review loop all work.

## Run tests

All test commands run from `src/bloggen/` (where `pyproject.toml` lives).

```bash
# All tests — no env vars needed, uses SQLite in-memory
uv run pytest -v

# Unit tests only
uv run pytest src/tests/unit/ -v

# Integration tests only
uv run pytest src/tests/integration/ -v
```

## Project structure

```
src/bloggen/            ← project root
├── src/
│   ├── bloggen/        ← Python package
│   │   ├── api/        ← FastAPI routers
│   │   ├── config/     ← Pydantic BaseSettings
│   │   ├── db/         ← SQLAlchemy models + repository
│   │   ├── domain/     ← Pydantic domain models
│   │   ├── graph/      ← LangGraph StateGraph + nodes
│   │   ├── tools/      ← Prompt builder (pure functions)
│   │   ├── prompts/    ← LLM prompt templates (.md)
│   │   ├── static/     ← HTML/JS single-page UI
│   │   └── observability/  ← structlog setup
│   └── tests/
│       ├── unit/       ← unit tests (no DB/LLM needed)
│       └── integration/← full pipeline tests (SQLite + stub LLM)
├── alembic/            ← database migrations
├── pyproject.toml
├── .env.example
└── README.md
```

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BLOGGEN_DATABASE_URL` | Yes | — | SQLAlchemy DB URL (e.g. `postgresql+psycopg2://...`) |
| `BLOGGEN_GEMINI_API_KEY` | No | `""` | Google Gemini API key (empty = stub mode) |
| `BLOGGEN_LLM_MODEL` | No | `gemini-2.0-flash` | Gemini model name |
| `BLOGGEN_LOG_LEVEL` | No | `INFO` | Log level |

## Known limitations (v0.1)

- Single-user; no authentication
- Article generation runs in a FastAPI background task (in-process, not queued)
- No auto-publishing to CMS platforms
- No SEO analysis, scheduling, or image generation
