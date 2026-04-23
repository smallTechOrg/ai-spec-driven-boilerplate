# Vision

## What This Agent Does

BlogForge is a single-user, local-first blog generator. The user defines a **Voice** (tone/style guidelines) and creates **Writer** personas that embody that voice. Through a simple web UI, the user picks a writer + topic; a LangGraph pipeline (plan → draft → finalize) calls Gemini to produce an **Article** persisted in PostgreSQL and viewable in the UI.

## Who Uses It

A solo content creator who wants consistent-voice blog drafts without prompting an LLM from scratch each time.

## Core Problem Being Solved

Pasting voice guidelines into chat for each article is lossy and inconsistent. BlogForge captures voice + writer persona as first-class data and reuses them deterministically.

## Success Criteria

- [ ] User can create a Voice and a Writer via the web UI
- [ ] User submits topic + writer → article is generated and saved
- [ ] Every article links to writer, voice, topic, timestamp
- [ ] No per-article prompt engineering required

## Out of Scope (v0.1)

- Article editing / regeneration / versioning
- Multi-writer debates
- Auth, multi-user
- Publishing / export integrations

## Key Constraints

- Local-only (no hosting)
- Single LLM provider: Google Gemini
- Latency: article in < 60s

## Phases

| Phase | Description | Gate |
|-------|-------------|------|
| 1 | Domain models (Voice, Writer, Article, AgentRun) + Postgres schema + repository | `uv run pytest tests/unit` green |
| 2 | LangGraph pipeline stubbed + FastAPI+Jinja UI + README | `uv run pytest` green, no API key required |
| 3 | Real Gemini integration | End-to-end article generated with real LLM |

## Future Phases

- Article editing / versioning / regeneration
- Export to markdown, publish to CMS
- Multi-writer editorial flow
- Voice auto-extraction from sample writing
