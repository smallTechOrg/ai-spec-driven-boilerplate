# DataChat

> **All commands run from the repo root** (where `pyproject.toml` and `alembic.ini` live). There is no subdirectory to `cd` into except where a command block says so explicitly.

A private, single-user, browser-based agent for ad-hoc analysis of your spreadsheet data (CSV/Excel).

You upload a file, the agent auto-profiles it, and you ask questions in plain language. The agent **writes pandas code, runs it locally, and answers with the real computed numbers** — and it shows you the exact code it ran.

**Privacy is the spine:** the raw data rows never leave your machine. The LLM (Gemini) only ever sees the *question*, the dataset *schema/profile*, and the *computed results* — never the rows themselves.

---

## Setup (one-time)

```bash
# from the repo root
cp .env.example .env
# edit .env and set your Gemini key:
#   AGENT_GEMINI_API_KEY=<your key>
uv sync
```

## Run

```bash
# from the repo root
uv run alembic upgrade head          # create the SQLite tables
uv run alembic current               # verify — must print a revision hash, not blank
cd frontend && pnpm install && pnpm build && cd ..   # build the static UI
uv run python -m src                 # start the server on http://localhost:8001
```

Then open **http://localhost:8001/app/** in your browser.

| URL | What |
|-----|------|
| `http://localhost:8001/app/` | The DataChat UI |
| `http://localhost:8001/health` | API health check |
| `http://localhost:8001/docs` | Interactive API docs (Swagger) |

## Tests

```bash
# from the repo root — runs against the real Gemini API using the key in .env
uv run pytest
```

---

## How it works

DataChat is a LangGraph agent. For each question it runs a bounded loop:

```
plan → generate pandas code → execute LOCALLY (raw rows never sent to the LLM) → inspect → finalize
```

- **Stack:** Python · FastAPI · LangGraph · pandas · SQLite · Gemini · Next.js (static, served at `/app/`).
- **Spec:** see `spec/` — `roadmap.md` (phases), `architecture.md`, `agent.md` (the graph), `capabilities/`.

This project is built phase by phase. See `spec/roadmap.md` for what each phase delivers.
