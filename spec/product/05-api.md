# API

## Style

Server-rendered HTML via FastAPI + Jinja2. No JSON API in v0.1.

## Routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Dashboard (list voices, writers, recent articles) |
| GET | `/voices` | List voices |
| GET | `/voices/new` | Voice form |
| POST | `/voices` | Create voice |
| GET | `/writers` | List writers |
| GET | `/writers/new` | Writer form |
| POST | `/writers` | Create writer |
| GET | `/articles` | List articles |
| GET | `/articles/new` | New article form (pick writer + topic) |
| POST | `/articles` | Generate article (invokes LangGraph synchronously) |
| GET | `/articles/{id}` | View article |
| GET | `/health` | JSON `{status:"ok"}` |

## Authentication

None (local single-user).
