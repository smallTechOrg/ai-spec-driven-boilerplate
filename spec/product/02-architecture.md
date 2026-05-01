# Architecture

## System Overview

Food Tracker is a single-process FastAPI application. A user uploads a food photo through a browser form. The server passes the image bytes through a three-step linear pipeline: receive → analyse → save. The analysis step calls Google Gemini Vision (or a local stub in offline mode) and returns structured nutrition data. Results are rendered back to the browser on the same page, and every result is saved to a local PostgreSQL database.

## Component Map

```
[Browser — upload form]
        ↓  multipart/form-data POST
[FastAPI router  /analyze]
        ↓
[Pipeline runner]
        ↓                      ↓
[node_analyse_food]     [node_save_log]
        ↓                      ↓
[LLMClient]           [PostgreSQL via SQLAlchemy]
        ↓
[Gemini Vision API]  (or StubProvider in demo mode)
```

## Layers

| Layer | Responsibility |
|-------|---------------|
| HTTP (FastAPI routers) | Accept multipart upload, return rendered HTML response |
| Pipeline (graph/runner.py) | Orchestrate node execution, carry state across steps |
| LLM (llm/) | Abstract Gemini Vision calls behind a provider interface |
| Domain (domain/) | Pydantic models for FoodLog, NutritionResult |
| DB (db/) | SQLAlchemy models, Alembic migrations, session management |
| Config (config/) | Pydantic BaseSettings, env var validation at startup |

## Data Flow

1. **Trigger:** User submits a food photo via `POST /analyze`
2. `node_analyse_food` passes image bytes to the LLM provider and parses the JSON response into a `NutritionResult`
3. `node_save_log` writes a `FoodLog` row to PostgreSQL
4. **Output:** FastAPI renders the result page with food name, calories, and macros

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Google Gemini Vision API | Identify food and estimate nutrition from the photo | Return HTTP 503 to the user; do not save a partial record |
| PostgreSQL | Persist every analysis result | Return HTTP 500; log the error; do not silently discard |

## Deployment Model

Runs as a local long-running FastAPI service (`uv run python -m food_tracker`) on port 8001. No containerisation required for v0.1.
