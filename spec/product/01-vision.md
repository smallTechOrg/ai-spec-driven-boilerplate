# Vision

> **Project:** BlogForge — Autonomous Blog Generator
> **Branch:** feat/blog-generator
> **Boilerplate:** This is a project-specific spec built on the ai-spec-driven-boilerplate template.

---

## What This Agent Does

BlogForge is an autonomous blog generation agent. Given a configured blog identity (name, niche, themes) and one or more writer personas (name, prompt, style), the agent independently selects topics — combining niche-aware brainstorming with real-time trending signals — then generates full blog posts (text + AI-generated cover images) and publishes them as a plain HTML + CSS static site. A web dashboard lets the operator configure everything and trigger generation runs manually or on a schedule.

## Who Uses It

**Primary user:** A solo blogger, content creator, or small team who wants a continuously publishing blog without manually writing every post. They set the blog up once, configure the writers and niche, and the agent handles the rest.

## Core Problem Being Solved

Writing consistently is hard. Topic ideation, drafting, and formatting take hours per post. BlogForge removes the manual labour entirely — the operator defines the voice and niche, and the agent produces ready-to-publish posts on its own schedule.

## Success Criteria

- [ ] Agent selects at least 3 distinct, non-repeating topics per generation run from the configured niche + trending signals
- [ ] Each generated post is 600–2000 words, structured (intro, headings, conclusion), attributed to a writer persona, and has a cover image
- [ ] Generated HTML site is browsable locally (index page + individual post pages) with no broken links
- [ ] Dashboard lets the operator configure blog settings, manage writers, and trigger a run — all without touching files
- [ ] Scheduled runs fire at the configured interval without manual intervention
- [ ] A post generated in one run does not repeat a topic from any previous run

## What This Agent Does NOT Do (Out of Scope)

- SEO optimisation, meta tags, or sitemap generation (future)
- Social media publishing or distribution (future)
- Comment systems or reader interaction (future)
- Human review / approval step before publishing (by design — fully autonomous)
- Multi-blog management (one blog instance per deployment)
- Custom domain or hosting setup (operator handles deployment)
- Video or audio content

## Key Constraints

- LLM and image provider: **Google Gemini only** (operator has no other API access)
  - Text: `gemini-2.0-flash` (or latest available Gemini model)
  - Images: Gemini Imagen API (`imagen-3.0-generate-002` or equivalent)
- Output must be valid, self-contained HTML + CSS — no JavaScript frameworks, no build step required to view
- All configuration and generated content persists in a local SQLite database
- The dashboard is a simple web UI served by the same process as the agent (no separate frontend deployment)

## Phases of Development

| Phase | Description | Success Gate |
|-------|-------------|--------------|
| 1 | Domain models + SQLite schema | Models defined, DB migrated, CRUD tests pass |
| 2 | Core agent loop — stubbed (hardcoded topic, no real LLM/image calls) | Runs end-to-end, produces an HTML file |
| 3 | Real LLM text generation via Gemini | Generated post reads like a coherent blog post |
| 4 | Real image generation via Gemini Imagen | Cover image saved, embedded in post HTML |
| 5 | Topic discovery (niche brainstorm + trending signals) | Agent picks 3+ distinct topics without repeating history |
| 6 | Scheduling (APScheduler) | Scheduled run fires at configured time |
| 7 | Web dashboard (FastAPI + HTML) | All dashboard screens functional |
| 8 | Integration tests | Full run from trigger to HTML output passes |
| 9 | Observability + polish | Every run logged; README accurate |
