# Vision

> **Project:** BlogForge — Autonomous Blog Generator
> **Branch:** feat/blog-generator
> **Boilerplate:** This is a project-specific spec built on the ai-spec-driven-boilerplate template.

---

## What This Agent Does

BlogForge is an autonomous blog generation agent. Given a configured blog identity (name, niche, themes) and one or more writer personas (name, prompt, style), the agent independently selects topics — combining niche-aware LLM brainstorming with real-time web search signals (DuckDuckGo + Tavily) — then generates full blog posts (text + AI-generated cover images) and stores them in a **content library** (SQLite DB). A web dashboard lets the operator configure everything, trigger generation runs, and browse the content library. Static HTML site export is a future phase.

## Who Uses It

**Primary user:** A solo blogger, content creator, or small team who wants a continuously growing content library without manually writing every post. They configure the blog identity and writers once, then the agent generates posts on demand or on a schedule.

## Core Problem Being Solved

Writing consistently is hard. Topic ideation, drafting, and formatting take hours per post. BlogForge removes the manual labour — the operator defines the voice and niche, and the agent populates the content library on its own schedule.

## Success Criteria

- [ ] Agent selects at least 3 distinct, non-repeating topics per run using DuckDuckGo + Tavily + Gemini brainstorm
- [ ] Each generated post is 600–2000 words, structured (intro, headings, conclusion), attributed to a writer persona, and has a cover image stored alongside it
- [ ] All posts are stored in the content library (SQLite) and viewable in the dashboard
- [ ] Dashboard lets the operator configure blog settings, manage writers, browse the content library, and trigger runs — all without touching files
- [ ] Scheduled runs fire at the configured interval without manual intervention
- [ ] A post does not repeat a topic from any previous run (case-insensitive deduplication via UsedTopic table)

## What This Agent Does NOT Do (Out of Scope — Initial Build)

- Static HTML site export (future phase — see `spec/product/capabilities/04-site-rendering.md`)
- SEO optimisation, meta tags, or sitemap generation (future)
- Social media publishing or distribution (future)
- Comment systems or reader interaction (future)
- Human review / approval step before posts enter the library (fully autonomous by design)
- Multi-blog management (one blog instance per deployment)
- Video or audio content

## Key Constraints

- LLM and image provider: **Google Gemini only** (operator has no other API access)
  - Text: `gemini-2.0-flash` (or latest available Gemini model)
  - Images: Gemini Imagen API (`imagen-3.0-generate-002` or equivalent)
- Topic signals: DuckDuckGo (free, no key) + Tavily (requires `TAVILY_API_KEY`)
- All configuration and generated content persists in a local SQLite database
- The dashboard is a simple web UI served by the same process as the agent (no separate frontend deployment)
- Cover images saved to local filesystem alongside the DB; paths stored in posts table

## Phases of Development

| Phase | Description | Success Gate |
|-------|-------------|--------------|
| 1 | Domain models + SQLite schema | Models defined, DB migrated, CRUD tests pass |
| 2 | Core agent loop — stubbed (hardcoded topic, no real LLM/image calls) | Runs end-to-end, post saved to DB |
| 3 | Real LLM text generation via Gemini | Generated post in DB reads like a coherent blog post |
| 4 | Real image generation via Gemini Imagen | Cover image saved to disk, path stored in DB |
| 5 | Topic discovery (DuckDuckGo + Tavily + Gemini brainstorm) | Agent picks 3+ distinct, non-repeating topics |
| 6 | Scheduling (APScheduler) | Scheduled run fires at configured cron time |
| 7 | Web dashboard (FastAPI + vanilla HTML) | All 4 dashboard tabs functional (Settings, Writers, Generate, Library) |
| 8 | Integration tests | Full run from trigger to content library entry passes |
| 9 | Observability + polish | Every run logged; README accurate |
| 10 | Static HTML export (future) | HTML site generated from content library |
