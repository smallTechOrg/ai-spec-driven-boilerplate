# Capabilities Index

## Capabilities in This Project

| # | Capability | Status | File |
|---|-----------|--------|------|
| 1 | Topic Discovery — DuckDuckGo + Tavily + Gemini brainstorm, dedup against history | Active | [01-topic-discovery.md](01-topic-discovery.md) |
| 2 | Post Generation — full Markdown post in a writer's voice via Gemini | Active | [02-post-generation.md](02-post-generation.md) |
| 3 | Image Generation — cover image via Gemini Imagen, SVG placeholder fallback | Active | [03-image-generation.md](03-image-generation.md) |
| 4 | Site Rendering — export content library to static HTML + CSS | **Future phase** | [04-site-rendering.md](04-site-rendering.md) |
| 5 | Writer Assignment — round-robin topic→writer pairing | Active | [05-writer-assignment.md](05-writer-assignment.md) |
| 6 | Scheduling — cron-based automatic runs via APScheduler | Active | [06-scheduling.md](06-scheduling.md) |

## Agent Graph Spec

See `spec/product/07-agent-graph.md` for the full LangGraph topology: state shape, node contracts, edge conditions, graph assembly, and error handling. This must exist and be reviewed before Phase 2 implementation begins.
