# Architecture

## System Overview

A FastAPI backend exposes upload, query, and session endpoints to a Next.js chat UI. Uploaded files are ingested into **DuckDB** (the analytical engine). A LangGraph agent turns a natural-language question + the dataset schema into SQL via a Gemini call, executes the SQL in DuckDB, and formats the result into an answer + table. Dataset metadata, sessions, messages, and the audit log live in the relational metadata DB (SQLAlchemy + Alembic). Every SQL execution is recorded in the audit log.

## Components

| Component | Responsibility | Location |
|-----------|----------------|----------|
| API layer | REST endpoints: upload, query, sessions | `src/api/` (`datasets.py`, `sessions.py`, existing `health.py`) |
| Ingest | Parse CSV/Excel → load into DuckDB; capture schema | `src/analytics/ingest.py` |
| DuckDB store | Owns the DuckDB connection; registers tables; runs SELECTs read-only | `src/analytics/duckdb_store.py` |
| Agent graph | NL + schema → SQL → execute → format | `src/graph/` |
| LLM client | Provider-agnostic Gemini call (already wired) | `src/llm/` |
| Metadata DB | datasets, sessions, messages, audit_log | `src/db/`, `alembic/` |
| Frontend | Chat UI: upload, messages, table; stubs for charts/dashboards/audit | `frontend/` |

## Data Flow (Phase 1 happy path)

1. `POST /datasets` (multipart CSV) → `ingest` loads it into DuckDB as table `ds_<id>`, captures column schema, writes a `Dataset` row.
2. `POST /sessions/{id}/query` with `{question}` → persists a user `Message`, invokes the graph.
3. Graph: `load_schema` reads the dataset's column names/types (from metadata, NOT DuckDB rows) → `generate_sql` (Gemini call: question + schema → SQL) → `execute_sql` (DuckDB SELECT, read-only) → `format_answer` (Gemini call: question + compact result preview → prose answer). `execute_sql` writes an `AuditLog` row.
4. Result `{answer, table, sql}` persisted as an assistant `Message` and returned.

## Token Economy {#token-economy}

- **Schema-only context:** `generate_sql` receives column names + DuckDB types only, never row data.
- **Compact prompts:** terse system prompts; schema rendered as `col_name: type` lines.
- **Result preview cap:** `format_answer` receives at most the first N rows (default 50) and the row count, not the full result set.
- **Minimal round-trips:** exactly two Gemini calls on the happy path; no speculative calls. The multi-step loop (Phase 4) is gated behind a complexity check so simple questions stay at two calls.
- **No raw-data egress:** uploaded rows live only in DuckDB; the LLM never sees source rows.

> **Assumed:** Phase 1 uses **two** Gemini calls (generate SQL, then format the answer) rather than a strict single call, because a faithful natural-language answer needs the actual result. A single-call variant would force the model to hallucinate the result. Both calls are schema/result-only — no raw input rows are ever sent.

## DuckDB vs Metadata DB split

- **DuckDB** (`src/analytics/duckdb_store.py`): the analytical engine. Holds dataset rows as columnar tables and runs the generated SELECTs. A single DuckDB file (`data/analytics.duckdb`) keeps multiple datasets queryable together (enables Phase 3 cross-dataset JOINs). Query execution is read-only (rejects non-SELECT statements).
- **Metadata DB** (`AGENT_DATABASE_URL`, SQLAlchemy): dataset metadata (id, name, DuckDB table name, schema JSON), sessions, messages, audit log. The durable record and the source of schema for the LLM.

## Audit Log Design

Table `audit_log` records every data operation. Columns: `id`, `session_id`, `dataset_id`, `operation` (e.g. `query`), `sql_text`, `status` (`success`/`error`), `row_count`, `error_message`, `duration_ms`, `created_at`. Written by `execute_sql` on both success and failure. Full schema in [data.md](data.md). The audit UI is Phase 5; the table and writes exist from Phase 1.

## Stack

- **Language:** Python 3.12 (backend), TypeScript (frontend).
- **Agent framework:** LangGraph (already wired in `src/graph/`).
- **LLM provider/model:** Gemini, default `gemini-2.5-flash`, via `AGENT_GEMINI_API_KEY`. Provider/model env-configurable (`AGENT_LLM_PROVIDER`, `AGENT_LLM_MODEL`); auto-detected from the set key. SDK: `google-genai`.
- **Analytical engine:** DuckDB (`duckdb` package) — single file `data/analytics.duckdb`.
- **Backend:** FastAPI + Uvicorn (port 8001).
- **Metadata/audit DB:** SQLAlchemy 2.x ORM + Alembic migrations, against `AGENT_DATABASE_URL`. **Assumed:** SQLite (`sqlite:///./data/agent.db`, per existing `.env`) — intake states no Postgres requirement and this is a single-tenant local tool. Alembic remains the migration path.
- **Frontend:** Next.js 15 + React 19.
- **Key libs:** `duckdb`, `pandas` (CSV/Excel parsing into DuckDB), `python-multipart` (upload), `openpyxl` (Phase 5 Excel). `pandas` is an ingest helper only — never used to send data to the LLM.
- **Dependency management:** uv (Python), pnpm (frontend). `duckdb`, `pandas`, `python-multipart` added to `[project.dependencies]`.

## Import Convention

Source is flattened under `src/` (pyproject `pythonpath=["src"]`). Imports use no package prefix: `from config.settings import get_settings`, `from analytics.duckdb_store import DuckDBStore`. Do NOT introduce `src/<package>/` nesting.
