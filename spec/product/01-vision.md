# Vision

## What This Agent Does

A web-based data analysis agent that lets users upload a CSV file and ask questions about their data in plain English. The agent uses a LangGraph ReAct loop backed by OpenRouter (Gemini 2.5 Flash by default) to generate and execute SQL queries against the full dataset iteratively until it has a confident answer. Results and query history are stored locally in SQLite and shown inline on the dataset page.

## Who Uses It

Data analysts, business users, and developers who have tabular data in CSV format and want quick answers without writing SQL or Python. They upload a file, type a question, and get an accurate answer immediately — derived from running real SQL against the full dataset, not a sample.

## Core Problem Being Solved

Querying and exploring CSV data typically requires coding skills (pandas, SQL) or expensive BI tools. This agent removes that barrier: any user can ask "What is the average revenue by region?" and get an answer instantly, without touching a terminal.

## Success Criteria

- [x] User can upload a CSV file via a web form and see it accepted
- [x] User can type a natural language question and receive a plain-text answer grounded in real SQL results
- [x] The agent runs multiple SQL queries iteratively and self-corrects on SQL errors before producing a final answer
- [x] Each query is stored in SQLite with the question, answer, token usage, cost estimate, and full SQL trace
- [x] The app runs fully in stub mode without an API key (for development)
- [x] The app starts with a single command and the UI is accessible at http://localhost:8001
- [x] Home page shows previous sessions; user can continue any session or delete it
- [x] Dataset page shows all past Q&A inline (no separate answer page)

## What This Agent Does NOT Do (Out of Scope for v0.1)

- Charts, visualizations, or dashboards (deferred to Phase 4)
- AI-written insight summaries (deferred to Phase 5)
- React/Vite frontend — v0.1 uses Jinja2 templates (React promoted to Phase 4)
- User authentication or multi-user support
- Multi-file or multi-dataset sessions

## Key Constraints

- OpenRouter API key is optional — app runs in stub mode without it
- SQLite only — no PostgreSQL required
- All commands run from the repo root with `uv run` prefix
- SQL execution is read-only (`SELECT` only); non-SELECT SQL is rejected

## Phases of Development

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Domain models + SQLite schema (Dataset, QueryRecord, AgentRun) | ✅ Done |
| 2 | Stubbed LangGraph pipeline + FastAPI UI end-to-end | ✅ Done |
| 3 | OpenRouter integration + iterative SQL ReAct loop + UI polish | ✅ Done |
| 4 | Charts and visualizations | Deferred |
| 5 | AI-written insights | Deferred |
