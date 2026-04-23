# Architecture

## System Overview

BlogForge runs as a single Python process. A FastAPI server exposes the web dashboard and an internal REST API. An embedded APScheduler fires generation runs on a cron schedule. The LangGraph agent executes the generation pipeline (topic discovery → post writing → image generation → site rendering) and persists results to SQLite. Generated HTML files are written to a configurable output directory.

## Component Map

```
[Dashboard UI]  ←HTTP→  [FastAPI Server]
                              │
                    ┌─────────┴────────────┐
                    │                      │
             [APScheduler]         [LangGraph Agent]
             (cron triggers)               │
                    │              ┌───────┴────────┐
                    └──────────────►               │
                                  [SQLite DB]  [Gemini API]
                                               (text + image)
                                       │
                                  [HTML Output Dir]
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| API (FastAPI) | Dashboard endpoints, run trigger, config CRUD, writer CRUD |
| Agent (LangGraph) | Orchestrates the generation pipeline; manages state across nodes |
| Tools | Individual functions: topic_discovery, write_post, generate_image, render_site |
| Domain | Pydantic models for Blog, Writer, Post, Run, Topic |
| Storage | SQLite via SQLAlchemy 2.0; generated HTML files on disk |
| LLM / Image | Google Gemini for text; Gemini Imagen for cover images |
| Scheduler | APScheduler (AsyncIOScheduler) for cron-based runs |

## Data Flow

1. **Trigger:** Dashboard button or APScheduler fires `POST /runs/trigger`
2. **Agent start:** LangGraph initialises `GenerationState` with blog config + writer list
3. **Topic discovery:** Agent queries Gemini for niche-aligned topics, cross-references Google Trends RSS, filters out previously used topics
4. **Post assignment:** Each topic is assigned to a writer via round-robin (see `spec/product/capabilities/05-writer-assignment.md`)
5. **Post generation:** For each topic+writer pair, Gemini generates the full post text
6. **Image generation:** Gemini Imagen generates a cover image for each post; saved to `output/images/`
7. **Site rendering:** Agent writes individual post HTML files + updates `index.html`
8. **Persist:** Posts saved to SQLite incrementally as each completes (not batched); run status transitions to `completed` only after all posts are rendered
9. **Done:** Run status updated to `completed`; dashboard reflects new posts

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Google Gemini API (text) | Post generation, topic brainstorming | Log error, mark run as failed, retry on next scheduled run |
| Google Gemini Imagen API | Cover image generation | Fall back to a placeholder SVG (see `spec/product/capabilities/03-image-generation.md`); post still published |
| Google Trends RSS | Trending topic signals | Skip trending signals; use niche-only brainstorming |
| SQLite | Config, posts, run history | Fatal — surface error immediately; do not start run |
| Local filesystem | HTML output directory | Fatal — surface error if output dir is not writable |

## Deployment Model

Single Python process run locally or on a VPS:

```bash
python -m blogforge serve   # starts FastAPI + APScheduler
```

The dashboard is served at `http://localhost:8000`. The generated site is in `./output/` (configurable). The operator is responsible for deploying `./output/` to a static host (Netlify, GitHub Pages, etc.).
