# Architecture

## System Overview

A single-process Python web app. The user submits a sourcing request via an HTML
form; FastAPI persists a `Run` row, then invokes a LangGraph state machine that
walks `research → enrich → score → finalize`. Each node reads/writes the run's
state and persists intermediate artifacts (suppliers, recommendations) to
PostgreSQL. When the graph terminates the user is redirected to a report page
that renders the ranked recommendations from the DB.

## Component Map

```
[Browser]
   │ POST /requests (form)
   ▼
[FastAPI app]  ──►  [LangGraph runner]
   │                    │
   │                    ├─► research node  ──►  [Search provider: Tavily | stub]
   │                    ├─► enrich node    ──►  [LLM provider: Gemini | stub]
   │                    ├─► score node     ──►  [LLM provider: Gemini | stub]
   │                    └─► finalize node
   │                    │
   ▼                    ▼
[Jinja2 templates]   [PostgreSQL: runs, sourcing_requests, suppliers, recommendations]
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| `api/` | FastAPI routes — form handling, server-rendered HTML responses |
| `graph/` | LangGraph state machine, nodes, edges, runner |
| `tools/` | Pure functions wrapping search + LLM (research, enrich, score) |
| `llm/` | Gemini provider + stub provider behind a common interface |
| `search/` | Tavily provider + stub provider behind a common interface |
| `db/` | SQLAlchemy models, session factory, init |
| `domain/` | Pydantic models used at module boundaries |
| `config/` | Pydantic Settings — env-driven, with `resolved_*` properties |
| `prompts/` | Markdown prompt templates loaded at runtime |

## Request Flow

1. `GET /` — renders the new sourcing request form.
2. `POST /requests` — validates input, creates `SourcingRequest` + `Run` rows,
   invokes `run_agent(request_id)` synchronously (v0.1).
3. The runner executes the graph. Stub mode returns canned data; real mode
   calls Tavily then Gemini.
4. Suppliers + recommendations are written; run status flips to `completed`
   (or `failed` with `error_message`).
5. User is redirected to `GET /runs/{run_id}` which renders the report.

## Stub vs. Real Resolution

`Settings.resolved_llm_provider` and `Settings.resolved_search_provider` are
the single source of truth. Each is computed from `provider` (`auto | gemini |
stub` / `auto | tavily | stub`) and the corresponding API key env var. The
template context always carries `llm_provider` and `search_provider`; the
base layout shows a yellow stub-mode banner whenever either resolves to
`stub`.
