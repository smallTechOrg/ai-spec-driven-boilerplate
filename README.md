# Local Data Analyst

A personal, local-first data analysis agent. Upload a CSV or Excel file, ask
questions in plain English, and get a trustworthy rich answer — plain-language
summary, key-stat callouts, an auto-picked chart, a summary table, a written
insight, and the exact DuckDB SQL that ran — all in seconds, on your own machine.

> **All commands run from the repo root** (where `pyproject.toml` and
> `alembic.ini` live). There is no subdirectory to `cd` into for backend
> commands. Every command is prefixed with `uv run`.

## The privacy boundary (why this is different)

Raw data rows **never leave your machine**. The agent runs all SQL locally in
DuckDB and sends only **column metadata (schema) and aggregate/summary numbers**
to the LLM (Gemini) for narration. This is enforced structurally in the agent
graph and verified by an automated test
(`tests/integration/test_privacy_boundary.py`) that captures every prompt sent
to Gemini and asserts no raw-row value ever appears in one.

## Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Node + [pnpm](https://pnpm.io/) (to build the static web UI)
- A Google Gemini API key

## Setup

1. Install dependencies (production + dev/test):

   ```bash
   uv sync --extra dev
   ```

2. Create your `.env` from the example and fill in your Gemini key:

   ```bash
   cp .env.example .env
   # then edit .env and set AGENT_GEMINI_API_KEY=...
   ```

   `.env` keys:

   | Key | Purpose | Default |
   |-----|---------|---------|
   | `AGENT_GEMINI_API_KEY` | Gemini API key (required) | — |
   | `AGENT_DATABASE_URL` | SQLite app-state DB | `sqlite:///./data/agent.db` |
   | `AGENT_LLM_MODEL` | LLM model | `gemini-2.5-flash` |
   | `AGENT_DATA_DIR` | Where uploaded files + caches live | `./data/datasets` |
   | `PORT` | Server port | `8001` |

## Run it

All commands from the repo root:

```bash
# 1. Apply database migrations
uv run alembic upgrade head

# 2. Verify the migration applied — this must print a revision (e.g. "0002 (head)"),
#    not blank output:
uv run alembic current

# 3. Build the static web UI
cd frontend && pnpm build && cd ..

# 4. Start the local service (boots FastAPI on port 8001)
uv run python -m src
```

Then open **http://localhost:8001/app/** (note the port `8001`, the `/app/`, and
the trailing slash).

## Using it (Phase 1)

1. Drag the shipped `samples/sample_sales.csv` onto the upload area (or use the
   file picker). A profile card appears: row count, columns + types, null counts,
   and basic stats. **(real)**
2. Type a question such as *"What were total sales by region?"* and submit.
   Within ~30s a rich answer appears: a plain-language answer, key-stat callouts,
   an auto-picked chart, a summary table, and a written insight. **(real)**
3. Expand the **Code / Steps / Profile** panel to see the exact DuckDB SQL, the
   plan steps, and the profile — plus the per-query token count and estimated USD
   cost. **(real)**

### What Phase 1 delivers

- Upload one CSV or Excel file (each Excel sheet becomes its own dataset) →
  auto-profile.
- Ask a plain-English question → plan → run DuckDB **locally** → narrate only
  the aggregates → rich answer with the exact SQL, plan steps, and per-query cost.
- Every ask is saved to an audit history (`GET /api/runs`, `GET /api/runs/{id}`).

### Labelled "Coming soon" stubs (not bugs)

These are visible but clearly labelled as non-functional in Phase 1; later phases
wire them up: a library sidebar, a watched folder, multi-file join, cross-day
session restore, a daily-cost total, and a reproducible re-run button. Follow-up
suggestion chips are shown but display-only in Phase 1.

## API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/datasets` | Upload a CSV/Excel file → datasets[] with profile |
| `POST` | `/api/ask` | Ask a question → rich-answer envelope (failed run = HTTP 200, `status:"failed"`, attempted SQL surfaced) |
| `GET`  | `/api/runs` | List the audit history (most recent first) |
| `GET`  | `/api/runs/{run_id}` | Full audit record for one run |
| `GET`  | `/health` | Health check |

All responses use the envelope `{"data": ..., "error": null}` on success and
`{"detail": {"code", "message"}}` on transport-level errors.

## Tests

Tests run against the **real Gemini API** (key from `.env`) and the production
SQLite driver:

```bash
uv run pytest tests/ -q
```

The Phase 1 gate:

```bash
uv run alembic upgrade head && uv run pytest tests/ -q
```

Integration tests `pytest.skip` only if `AGENT_GEMINI_API_KEY` is genuinely
absent — a skipped real-key test is not a passing gate.

## Architecture (short)

- **API** (`src/api/`) — FastAPI REST.
- **Agent graph** (`src/graph/`) — LangGraph PLAN-THEN-EXECUTE: `profile → plan →
  local_execute → aggregate → narrate → suggest_follow_ups → finalize`, with
  `handle_error` on any fatal node.
- **Data engine** (`src/data/`) — CSV/Excel ingestion, the auto-profiler, the
  local read-only DuckDB query runner, and cost estimation. The privacy boundary
  lives here: aggregates out, raw rows never out.
- **LLM** (`src/llm/`) — Gemini provider (`gemini-2.5-flash`) with real token
  usage capture.
- **Persistence** (`src/db/`) — SQLite app state (dataset library, conversation
  messages, run audit) via SQLAlchemy 2.0 + Alembic. DuckDB holds the raw rows;
  SQLite never does.
