# Architecture

## System Overview

The data analysis agent is a single-process FastAPI application. Users interact via a browser UI (Jinja2 templates). Uploaded CSVs are stored on disk; metadata and query history live in SQLite. Each natural language query triggers a LangGraph pipeline that sends the data schema + user question to Google Gemini, receives a plain-text answer, and persists the result.

## Component Map

```
Browser (HTML form)
    ↓ POST /upload
FastAPI (uvicorn)
    ↓
LangGraph Pipeline
    ├── load_data node    (parse CSV with pandas)
    ├── analyze node      (send schema + question to Gemini)
    └── finalize node     (persist QueryRecord to SQLite)
    ↓
SQLite (via SQLAlchemy 2.0)
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| API (FastAPI) | HTTP routing, file upload, form handling, template rendering |
| Graph (LangGraph) | Agent pipeline: parse → analyze → finalize |
| LLM (google-genai) | Gemini API calls; falls back to stub when key not set |
| Domain | Pydantic models for Dataset and QueryRecord |
| DB (SQLAlchemy + SQLite) | Persistence of datasets and query history |
| Templates (Jinja2) | Server-rendered HTML: upload form, results page, history |

## Data Flow

1. Trigger: User uploads a CSV file via browser form (POST /upload)
2. FastAPI saves the file, creates a `Dataset` DB record
3. User types a natural language question (POST /query)
4. LangGraph pipeline: `load_data` → `analyze` (Gemini/stub) → `finalize`
5. `finalize` writes a `QueryRecord` to SQLite with question, answer, timestamp
6. FastAPI renders the answer page with the result and a link back to ask another question

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Google Gemini API | NL reasoning over CSV schema | Falls back to stub — answer marked as "(stub mode)" |
| SQLite | Store datasets and query history | App fails to start if DB file is unwritable |
| Local filesystem | Store uploaded CSV files | Upload fails with user-visible error |

## Deployment Model

Local single-user service. Runs with `uv run python -m data_analysis_agent` on port 8001. No container required for v0.1.
