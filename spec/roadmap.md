# Roadmap

## What This Agent Does

The Data Analyst Agent is a browser-based conversational assistant that lets users upload CSV or Excel files, builds a personal dataset catalogue backed by DuckDB, and answers natural-language questions about that data. For each question the agent selects relevant tables, writes and executes SQL via DuckDB, and returns a formatted markdown result table alongside a concise analytical narrative — reproducing the reasoning of a senior data analyst: clarifying ambiguous intent, decomposing multi-step questions into sub-queries, surfacing data quality notes (nulls, outliers, type mismatches), and suggesting follow-up angles.

## Who Uses It

**Primary user:** A data analyst, researcher, or business user who has tabular data files (CSV or Excel) and wants to interrogate them conversationally without writing SQL or setting up a database. They work alone in a local or private deployment and do not require multi-user access or authentication.

## Core Problem Being Solved

Exploring unfamiliar tabular datasets today requires knowing SQL, setting up a database, and often waiting for an engineer. This agent removes all three barriers: files are uploaded through a web UI, DuckDB registers them instantly, and the LLM translates plain-English questions into SQL — letting non-technical or time-pressed users get answers from their data in seconds.

## Success Criteria

- [ ] A user can upload a CSV or Excel file and see it appear in the dataset catalogue with correct name, schema, and row count within 5 seconds of upload completing.
- [ ] A natural-language question about an uploaded dataset returns a correct SQL result (matching a manually-verified query) and a coherent narrative response within 30 seconds on typical hardware.
- [ ] Every SQL execution (including errors and zero-row results) is recorded in the audit log with all required fields: timestamp, session_id, question, generated SQL, datasets touched, row count returned, and latency_ms.
- [ ] A conversation session — including history and dataset catalogue — survives a server restart (data is read back correctly from SQLite).
- [ ] The agent refuses to execute destructive SQL (DROP, DELETE, TRUNCATE, ALTER) and returns a clear refusal message to the user.
- [ ] An ambiguous question (one that could apply to multiple tables or is underspecified) results in the agent asking a clarifying question rather than guessing silently.

## What This Agent Does NOT Do (Out of Scope for v1)

- **Charts and visualisations** — no chart rendering; markdown tables only. Deferred to v2.
- **Multi-user / authentication** — single-user local deployment; no login, no per-user isolation.
- **Dataset sharing or export** — no export of results or sharing of sessions.
- **Scheduled or triggered queries** — agent responds to interactive chat only; no cron or webhook triggers.
- **Write-back to user files** — query results are never written back to source files.
- **Docker / cloud deployment** — local `uvicorn` server only for v1.
- **Vector / semantic search over data** — SQL only; no embedding-based retrieval.
- **Streaming responses** — responses are returned in full after LLM completion, not streamed token-by-token.
- **Dataset versioning** — uploaded files are immutable; no version history or diff.
- **Soft-delete / hard-delete of datasets** — files on disk are never removed automatically. Soft-delete (hide from catalogue) is a v1 API endpoint but the file and DuckDB registration remain.

## Key Constraints

- `GEMINI_API_KEY` must be present in `.env`; no fallback to a stub LLM in any test or production path.
- The audit log is append-only: no entries are ever deleted or updated.
- Uploaded files are never deleted from `data/uploads/` automatically.
- The agent must refuse destructive SQL (`DROP`, `DELETE`, `TRUNCATE`, `ALTER`) on any table.
- All tests run against the real Gemini API; no mocked LLM calls.
- API key must never be echoed to logs, committed to git, or returned in any API response.
- DuckDB is in-process; no separate database server is required.
- The frontend requires no build step — vanilla HTML/JS, served as a static file by FastAPI.

## Phases of Development

| Phase | Description | Success Gate |
|-------|-------------|--------------|
| 1 | Core data layer: file upload, DuckDB registration, SQLite catalogue and session persistence, audit log. No LLM yet. | Unit tests pass: CSV/Excel upload stores file, registers DuckDB table, writes catalogue row, writes audit log entry, survives SQLite round-trip. |
| 2 | Full agent loop: NL→SQL via Gemini tool-use, response synthesis, conversation history with summarisation, token-economy schema filtering. Frontend single-page UI wired to all endpoints. | Integration tests pass: upload → NL question → SQL executed → audit entry written → markdown response returned. Golden-path smoke: upload file, 3 sequential questions, server restart, session intact. Edge cases: empty file, malformed CSV, zero-row result, no-matching-table, ambiguous question, destructive SQL refused. |

## Future Phases

- **v2 — Charts and dashboards:** Chart.js or Vega-Lite rendering of query results; user can pin charts to a dashboard.
- **v2 — Streaming responses:** Token-by-token SSE streaming from Gemini to the browser.
- **v2 — Dataset versioning:** Track file revisions; allow re-upload of updated dataset.
- **v3 — Multi-user / auth:** Per-user session isolation, login, and dataset ownership.
- **v3 — Cloud deployment:** Docker image, environment-variable config for cloud hosting.
- **v3 — Semantic dataset search:** Embedding-based retrieval to find relevant tables when the catalogue is large (>50 tables).
- **v3 — Scheduled queries:** Cron-triggered queries that email or Slack results.
