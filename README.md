# Data Analyst Agent

> **Run every command below from the repo root.** The repo root *is* the project — there is no subdirectory to `cd` into, with one exception: the one-off frontend build, which runs from `frontend/` (and returns to root). Every command block states its working directory explicitly.

A local-first data-analyst agent. Upload a CSV, ask a question in plain English, and get back a formatted-text answer plus a data table — produced by SQL the LLM generates and that runs locally against a real SQLite table. Every ingest and every query is recorded in a full audit trail (timestamp, exact SQL, row count, columns, duration, success/error), and the uploaded dataset plus the query history persist across page reloads (re-fetched from SQLite). It is token-economical by design: the LLM only ever sees a table's schema, a small row sample (≤ 20 rows), and query result sets — never the full dataset, which never leaves your machine.

**Stack:** Python + FastAPI + LangGraph + SQLite + Next.js (static export, single-origin) + Google Gemini (`gemini-2.5-flash`).

---

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) — Python environment + command runner
- [`pnpm`](https://pnpm.io/) — to build the frontend (one-off)
- A **Google Gemini API key**

---

## Setup

The only manual step is providing your Gemini API key.

Working directory: **repo root** (`/Users/sai/Workspace/Code/exp1`)

```bash
cp .env.example .env
# edit .env and set:
#   AGENT_GEMINI_API_KEY=<your Google Gemini API key>
```

`.env` is gitignored — your key is never committed.

---

## Run

All commands run from the **repo root** unless a block says otherwise.

### 1. Apply the database migration

Working directory: **repo root**

```bash
uv run alembic upgrade head
uv run alembic current
```

`uv run alembic current` should print a revision (e.g. `0001 (head)`), confirming the migration applied. A blank result means it did not — re-run `upgrade head`.

### 2. Build the frontend (one-off)

This is the only step that runs from a subdirectory. It produces `frontend/out/`, which FastAPI serves at `/app`.

Working directory: **`frontend/`** (then back to repo root)

```bash
cd frontend && pnpm install && pnpm build && cd ..
```

### 3. Start the server

Working directory: **repo root**

```bash
uv run python -m src
```

This starts uvicorn on **port 8001**.

### 4. Open the app

In your browser, open:

```
http://localhost:8001/app/
```

Note the port (`8001`), the `/app/` path, and the **trailing slash**.

---

## Try it

1. **Upload a small CSV** (e.g. a sales export). You'll see a confirmation with the table name, row count, and the detected columns — and an audit entry appears for the ingest.
2. **Ask a question** in plain English, e.g. `What is the total revenue by region?`. You'll get a formatted-text answer plus a data table of the result, and a second audit entry showing the exact generated SQL, row count, columns, and duration.
3. **Open the Audit panel** — both operations are listed with timestamps and the SQL that ran.
4. **Reload the page** — the dataset is still selected and the previous question, answer, and full audit/query history are all still there (re-fetched from SQLite).

---

## Run the tests

Working directory: **repo root**

```bash
uv run pytest
```

The suite runs against the **real Gemini API** using the key in `.env` — there are no stubbed LLM calls, and it uses the production SQLite driver.

---

## What's real in Phase 1 vs. coming later

**Real and working now (Phase 1):**

- Single-CSV upload → a real, queryable SQLite table with inferred column types
- Natural-language question → text-to-SQL → formatted-text answer + data table
- Full audit trail (timestamp, exact SQL, row count, columns, duration, success/error)
- Persistent session — dataset and query history survive a page reload

**Clearly-labelled stubs in the UI ("Coming soon" — not bugs):**

- **Multi-dataset manager + cross-dataset joins** — Phase 2
- **Charts** (bar / line / pie) — Phase 3
- **Dashboards** (pin answers/charts, persisted) — Phase 4
- **Senior-analyst workflow** (multi-step plan → query → synthesize) — Phase 5

These stubs are visible to convey the product vision and are intentionally non-functional in Phase 1.

---

## Architecture & layout

The full design lives in [`spec/`](spec/):

- [`spec/roadmap.md`](spec/roadmap.md) — what the agent does, success criteria, and the phased plan
- [`spec/architecture.md`](spec/architecture.md) — the chosen stack, the read-only SQL sandbox, and project layout
- [`spec/agent.md`](spec/agent.md) — the LangGraph text-to-SQL flow and the token-economy contract
- [`spec/data.md`](spec/data.md) — entities and fields (datasets, queries, audit log)
- [`spec/api.md`](spec/api.md) — the request/response contract (`/datasets`, `/queries`, `/audit`)
- [`spec/ui.md`](spec/ui.md) — the single-page data-analyst UI and its states
