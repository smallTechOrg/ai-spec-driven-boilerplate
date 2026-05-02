# Architecture

## System Overview

The UP Police AI Workshop is a server-rendered Python web application. Officers interact via a browser; the FastAPI/Jinja2 server handles all routing, session management, and database operations. There is no client-side JavaScript framework — all pages are server-rendered HTML with embedded CSS.

## Component Map

```
[Browser (Officer)]
        ↓
[FastAPI App — port 8001]
    ├── /              (landing + session check)
    ├── /register      (officer self-registration)
    ├── /assessment    (20-question form)
    ├── /plan          (30-day plan dashboard)
    └── /health        (health check)
        ↓
[Service Layer]
    └── plan_generator.py  (rule-based 30-day plan generation)
        ↓
[PostgreSQL — up_police_ai_dev]
    ├── officers
    ├── assessments
    ├── learning_plans
    └── plan_days
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| API (api/) | Request routing, session validation, form parsing, template rendering |
| Services (services/) | Business logic — plan generation from assessment scores |
| Domain (domain/) | Pydantic models for type safety across layers |
| DB (db/) | SQLAlchemy ORM models, engine, session management |
| Data (data/) | Static task lookup table (60 tasks × 4 areas × 3 levels) |
| Templates (templates/) | Jinja2 HTML templates, self-contained CSS |

## Data Flow

1. Officer visits `/` — server checks session cookie for officer_id
2. If not registered, redirected to `/register` — form submission creates officer row, sets session
3. Officer completes 20-question assessment at `/assessment` — form POST computes section averages
4. Plan generator creates 30 PlanDayRow entries based on section averages and level thresholds
5. Officer views dashboard at `/plan` — sees all 30 days, can update each day's status
6. Status updates POST to `/plan/day/{day_id}/status` — updates DB row, redirects back to plan

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| PostgreSQL | Persistent storage for officers, assessments, plans | App returns 500; data loss if DB unavailable |

## Deployment Model

Single-process uvicorn server. Run with `uv run python -m up_police_ai`. Port 8001. Configuration via `.env` file with `UPPOLICE_` prefix.
