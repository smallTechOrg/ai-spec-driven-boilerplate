# Vision

## What This Agent Does

A web-based data analysis agent that lets users upload a CSV file and ask questions about their data in plain English. The agent uses a LangGraph pipeline backed by Google Gemini to understand the data structure and answer natural language questions with accurate, plain-text responses. Results and query history are stored locally in SQLite.

## Who Uses It

Data analysts, business users, and developers who have tabular data in CSV format and want quick answers without writing SQL or Python. They upload a file, type a question, and get an answer immediately.

## Core Problem Being Solved

Querying and exploring CSV data typically requires coding skills (pandas, SQL) or expensive BI tools. This agent removes that barrier: any user can ask "What is the average revenue by region?" and get an answer instantly, without touching a terminal.

## Success Criteria

- [ ] User can upload a CSV file via a web form and see it accepted
- [ ] User can type a natural language question and receive a plain-text answer grounded in the data
- [ ] Each query is stored in SQLite with the question, answer, and timestamp
- [ ] The agent runs fully offline (stub mode) without an API key for development
- [ ] The app starts with a single command and the UI is accessible at http://localhost:8001

## What This Agent Does NOT Do (Out of Scope for v0.1)

- Charts, visualizations, or dashboards (deferred to Phase 3)
- AI-written insight summaries (deferred to Phase 3)
- React/Vite frontend — v0.1 uses Jinja2 templates (React promoted in Phase 4)
- User authentication or multi-user support
- Multi-file or multi-dataset sessions

## Key Constraints

- Gemini API key is optional — app must run in stub mode without it
- SQLite only — no PostgreSQL required
- All commands run from the repo root with `uv run` prefix

## Phases of Development

| Phase | Description | Success Gate |
|-------|-------------|--------------|
| 1 | Domain models + SQLite schema (Dataset, Query) | `uv run pytest tests/unit/` 100% |
| 2 | Stubbed LangGraph pipeline + FastAPI UI end-to-end | `uv run pytest` + live curl at `/health` |
| 3 | Real Gemini integration replacing stub | Real answers returned for a sample CSV |
| 4 | Charts and visualizations | Bar/line/pie charts rendered in browser |
| 5 | AI-written insights | Auto-generated summary paragraph per upload |
