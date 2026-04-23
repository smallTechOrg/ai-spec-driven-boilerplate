# Architecture

## System Overview

BlogForge runs as a single Python process. A FastAPI server exposes the web dashboard and an internal REST API. An embedded APScheduler fires generation runs on a cron schedule. The LangGraph agent executes the generation pipeline (topic discovery → post writing → image generation → content library) and persists results to SQLite. Cover images are saved to a local `./images/` directory. The dashboard serves as the primary interface for browsing the content library.

## Component Map

```
[Dashboard UI]  ←HTTP→  [FastAPI Server]
                              │
                    ┌─────────┴────────────┐
                    │                      │
             [APScheduler]         [LangGraph Agent]
             (cron triggers)               │
                    │        ┌─────────────┴──────────────┐
                    └────────►                            │
                             [SQLite DB]         [External APIs]
                             (content library)   ┌──────────────────┐
                                       │         │ Gemini (text)    │
                                  [./images/]    │ Gemini Imagen    │
                                  (cover imgs)   │ DuckDuckGo       │
                                                 │ Tavily           │
                                                 └──────────────────┘
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| API (FastAPI) | Dashboard endpoints, run trigger, config CRUD, writer CRUD, posts CRUD |
| Agent (LangGraph) | Orchestrates the generation pipeline; manages state across nodes |
| Tools | Pure functions: topic_discovery, write_post, generate_image, save_to_library |
| Domain | Pydantic models for Blog, Writer, Post, Run, Topic |
| Storage | SQLite via SQLAlchemy 2.0; cover images on local filesystem |
| LLM / Image | Google Gemini for text; Gemini Imagen for cover images |
| Search | DuckDuckGo (free) + Tavily (API key) for trending topic signals |
| Scheduler | APScheduler (AsyncIOScheduler) for cron-based runs |

## Data Flow

1. **Trigger:** Dashboard button or APScheduler fires `POST /runs/trigger`
2. **Agent start:** LangGraph initialises `GenerationState` with blog config + writer list
3. **Topic discovery:** DuckDuckGo + Tavily searched in parallel for niche-trending topics; Gemini brainstorms additional candidates; all merged, deduplicated, and filtered against UsedTopic history
4. **Post assignment:** Each topic assigned to a writer via round-robin (see `spec/product/capabilities/05-writer-assignment.md`)
5. **Post generation:** For each topic+writer pair, Gemini generates full Markdown post text
6. **Image generation:** Gemini Imagen generates a cover image per post; saved to `./images/post-{id}-cover.png`
7. **Persist:** Each completed post saved to SQLite content library incrementally (not batched)
8. **Done:** Run status transitions to `completed`; dashboard Library tab reflects new posts

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Google Gemini API (text) | Post generation, topic brainstorming | Log error, mark run as failed |
| Google Gemini Imagen API | Cover image generation | Fall back to placeholder SVG (see `spec/product/capabilities/03-image-generation.md`); post still saved |
| DuckDuckGo Search | Trending topic signals (free, no key) | Skip; continue with Tavily + LLM brainstorm |
| Tavily Search API | Trending topic signals (richer results) | Skip; continue with DuckDuckGo + LLM brainstorm |
| SQLite | Content library, config, run history | Fatal — surface error immediately; do not start run |
| Local filesystem | Cover image storage (`./images/`) | Fall back to placeholder SVG; post still saved |

## Deployment Model

Single Python process run locally or on a VPS:

```bash
python -m blogforge serve   # starts FastAPI + APScheduler
```

Dashboard served at `http://localhost:8000`. Cover images at `./images/` (relative to working directory). No separate deployment needed for the content library — everything is in the local SQLite DB and dashboard.
