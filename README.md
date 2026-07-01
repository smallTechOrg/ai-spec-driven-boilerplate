# CSV Data Analysis Agent

> All commands run from the repo root: `c:\Users\Lenovo\claude_agent_workshop\data-analysis-agent`

Conversational data analysis assistant: upload a CSV, get an auto-profile, ask natural-language questions, receive text answers with interactive Plotly charts. Backed by Gemini (gemini-2.0-flash by default) via LangGraph. Session-only — no data persists after the session ends.

## Setup

1. Copy `.env.example` to `.env` and fill in `AGENT_GEMINI_API_KEY`.
2. Install Python dependencies: `uv sync --extra dev`
3. Install frontend dependencies: `cd frontend && pnpm install && cd ..`

## Run (Phase 1)

```bash
# 1. Apply database migrations
uv run alembic upgrade head
uv run alembic current   # must show a revision hash

# 2. Build the frontend
cd frontend && pnpm build && cd ..

# 3. Start the server
uv run python -m src
```

Open http://localhost:8001/app/ — upload a CSV file, ask questions, see charts.

## Test

```bash
uv run python -m pytest tests/ -v
```

Tests that call the real Gemini API require `AGENT_GEMINI_API_KEY` set in `.env`.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AGENT_GEMINI_API_KEY | Yes | — | Gemini API key |
| AGENT_DATABASE_URL | No | sqlite:///./data/agent.db | SQLite DB path |
| AGENT_LLM_MODEL | No | gemini-2.0-flash | LLM model name |
| AGENT_TEMP_DIR | No | OS temp dir | Directory for uploaded CSV temp files |
| PORT | No | 8001 | Server port |

## Architecture

- **Frontend:** Next.js 15 static export at /app (built with pnpm build)
- **Backend:** FastAPI on port 8001
- **Agent:** LangGraph (profile_graph + qa_graph)
- **LLM:** Gemini gemini-2.0-flash (via google-genai)
- **DB:** SQLite (session-scoped metadata only)
- **Privacy:** Raw CSV row values never sent to LLM — only schema + statistical summaries

## Phase 1 capabilities (real)
- Upload a single CSV → auto-profile card (row count, column types, nulls, quality flags)
- Ask a natural-language question → text answer + interactive Plotly chart in chat
- Multi-turn conversation with full session history

## Coming in Phase 2
- Multi-file analysis and joins
- Excel (.xlsx) support
- Export results as CSV
