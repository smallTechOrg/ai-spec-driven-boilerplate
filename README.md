# DataChat

A browser web app for uploading CSV/JSON datasets and asking plain-English questions about your data. Powered by a Google Gemini ReAct agent that reasons over your data iteratively using sandboxed pandas operations.

> **All commands run from the repo root.**

## Quick Start

### 1. Install dependencies

```bash
# From: repo root
uv sync
```

### 2. Configure environment

```bash
# From: repo root
cp .env.example .env
# Edit .env and set DATA_ANALYST_GEMINI_API_KEY=your-key-here
```

### 3. Apply database migrations

```bash
# From: repo root
uv run alembic upgrade head
uv run alembic current    # must show a revision hash — blank = migration not applied
```

### 4. Run the server

```bash
# From: repo root
uv run python -m data_analyst
```

Server starts at **http://localhost:8001**

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATA_ANALYST_DATABASE_URL` | No | `sqlite:///./data_analyst.db` | SQLite DB path |
| `DATA_ANALYST_GEMINI_API_KEY` | Yes (for live mode) | `` | Your Google Gemini API key |
| `DATA_ANALYST_LLM_MODEL` | No | `gemini-2.5-flash` | Gemini model name |
| `DATA_ANALYST_MAX_ITERATIONS` | No | `10` | Max ReAct loop iterations per question |
| `DATA_ANALYST_MAX_UPLOAD_BYTES` | No | `52428800` | Max file size (default 50MB) |
| `DATA_ANALYST_LOG_LEVEL` | No | `INFO` | Log level |
| `PORT` | No | `8001` | HTTP port |

**Stub mode:** If `DATA_ANALYST_GEMINI_API_KEY` is not set, the app runs in stub mode — all LLM calls return deterministic placeholder responses. Set the API key to switch to live Gemini automatically.

---

## Running Tests

```bash
# From: repo root
uv run pytest tests/unit/ -v        # unit tests only
uv run pytest tests/ -v             # all tests — no API key required
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check + current LLM provider |
| `POST` | `/api/sessions` | Upload a CSV or JSON file |
| `GET` | `/api/sessions/{id}` | Get session metadata |
| `GET` | `/api/sessions/{id}/messages` | Get chat history |
| `POST` | `/api/sessions/{id}/messages` | Ask a question about the dataset |

### Upload a file

```bash
curl -X POST http://localhost:8001/api/sessions \
  -F "file=@data.csv"
```

### Ask a question

```bash
curl -X POST http://localhost:8001/api/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the average value in column X?"}'
```

---

## Project Layout

```
src/data_analyst/     ← Python package
  api/                ← FastAPI routers (health, sessions, chat)
  config/             ← Settings (Pydantic BaseSettings, DATA_ANALYST_ prefix)
  db/                 ← SQLAlchemy models + session factory
  domain/             ← Pydantic domain models
  graph/              ← LangGraph ReAct agent (state, nodes, edges, runner)
  llm/                ← LLM provider abstraction (Gemini + stub)
  tools/              ← pandas_executor (sandboxed read-only operations)
tests/
  unit/               ← Unit tests (no DB, no LLM)
  integration/        ← Integration + golden-path smoke tests
alembic/              ← Database migrations
```

---

## Deferred (Future Phases)

- Visual dashboards and charts
- Automated data profiling and insights
- Multi-user authentication
- Export / download results
- Multi-file uploads per session
