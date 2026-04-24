# EU Lead Gen Agent

> **All commands run from the repo root.**

Discovers and enriches small-to-medium European businesses that lack an in-house data function — prime candidates for a data consultancy pitch. Powered by Google Gemini + LangGraph. Results are stored in PostgreSQL and browsable in a web dashboard with CSV export.

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- PostgreSQL running locally

---

## Setup

### 1. Install dependencies

```bash
# from repo root
uv sync
```

### 2. Create databases

```bash
# from repo root
psql -U postgres -c "CREATE DATABASE lead_gen_agent;"
psql -U postgres -c "CREATE DATABASE lead_gen_agent_test;"
```

### 3. Configure environment

```bash
# from repo root
cp .env.example .env
```

Edit `.env` and set:

| Variable | Description |
|----------|-------------|
| `LGA_DATABASE_URL` | PostgreSQL connection string for the app DB |
| `LGA_TEST_DATABASE_URL` | PostgreSQL connection string for the test DB |
| `LGA_GEMINI_API_KEY` | Your Google Gemini API key (leave blank for stub mode) |
| `LGA_LLM_MODEL` | Gemini model name (default: `gemini-2.5-flash`) |
| `LGA_LLM_PROVIDER` | `auto` — resolves to `gemini` when key is set, `stub` otherwise |

### 4. Apply database migrations

```bash
# from repo root
uv run alembic upgrade head
uv run alembic current
```

`alembic current` must show a revision hash (e.g. `abe038cd88bd (head)`). Blank output means the migration was not applied.

---

## Run the app

```bash
# from repo root
uv run python -m lead_gen_agent
```

Open http://localhost:8001 in your browser.

- **No API key set** → stub mode (simulated leads, yellow banner on every page)
- **API key set** → live mode (real Gemini calls)

---

## Run tests

Tests require `LGA_DATABASE_URL` pointing at a real PostgreSQL test database.

```bash
# from repo root
LGA_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/lead_gen_agent_test uv run pytest -q
```

All tests run fully offline — no LLM API key required.

---

## How to use

1. Open http://localhost:8001/runs/new
2. Select a country, enter an industry (e.g. `retail`, `logistics`), optionally set headcount range
3. Click **Find Leads** — the agent runs the full discovery + enrichment pipeline
4. Browse results on the run results page or the main dashboard
5. Click **Export CSV** to download leads for your outreach tool

---

## Project layout

```
src/lead_gen_agent/
├── api/            FastAPI routes + app factory
├── config/         Pydantic settings (env prefix: LGA_)
├── db/             SQLAlchemy models, session, repository
├── domain/         Pydantic domain models (Lead, SearchRun, ...)
├── graph/          LangGraph pipeline (state, nodes, edges, runner)
├── llm/            LLM provider layer (Gemini + stub)
└── templates/      Jinja2 HTML templates
tests/
├── unit/           Unit tests (smoke, DB repository, graph compile)
└── integration/    Golden-path end-to-end smoke test
alembic/            Database migrations
```

---

## What is deferred (Phase 3+)

- Live Gemini calls for real lead discovery (Phase 3)
- Deep enrichment: org structure, financials, lines of business (Phase 4)
- AI-generated personalised outreach copy per lead (Phase 5)
- Email / contact-person discovery
- Lead scoring model
- CRM integration
