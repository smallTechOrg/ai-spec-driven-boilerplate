# UP Police AI Workshop

A learning progress tracker and self-assessment tool for Uttar Pradesh Police staff.

## What It Does

1. **Self-register**: Officer enters name + badge number — creates a profile (cookie-based session, no password)
2. **Self-assessment**: 20 questions across 4 sections (5 each), scored 1–5
3. **30-day learning plan**: Auto-generated from scores. Each day has a Focus Area, Level (Beginner/Intermediate/Advanced), task description, and resource link
4. **Progress tracking**: Officers mark days as "Done", "In Progress", or "Not Started". Progress bar shows X/30 complete.

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL (running locally)
- `uv` package manager

### Setup

```bash
# Clone and install
git clone <repo-url>
cd ai-spec-driven-boilerplate
cp .env.example .env

# Create databases
createdb up_police_ai_dev
createdb up_police_ai_test

# Install dependencies
uv sync --extra dev

# Run database migrations
uv run alembic upgrade head

# Start the server (port 8001)
uv run python -m up_police_ai
```

Visit http://localhost:8001

### Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description | Default |
|----------|-------------|---------|
| `UPPOLICE_DATABASE_URL` | PostgreSQL connection URL | required |
| `UPPOLICE_SECRET_KEY` | Session cookie signing key | dev-secret-key-change-in-production |
| `UPPOLICE_LOG_LEVEL` | Log level | INFO |

## Development

### Run tests

```bash
# Unit tests only
DATABASE_URL=postgresql://localhost/up_police_ai_test uv run pytest tests/unit/ -v

# All tests (unit + integration)
DATABASE_URL=postgresql://localhost/up_police_ai_test uv run pytest tests/ -v

# With coverage
DATABASE_URL=postgresql://localhost/up_police_ai_test uv run pytest tests/ --cov=src/up_police_ai
```

### Project Layout

```
src/up_police_ai/
├── api/                  FastAPI routes + Jinja2 templates
├── config/               Pydantic settings (UPPOLICE_ prefix)
├── data/                 Task lookup table (60 tasks)
├── db/                   SQLAlchemy ORM models + session
├── domain/               Pydantic domain models
├── services/             Plan generation logic
├── static/               Static assets
└── templates/            Jinja2 HTML templates
tests/
├── unit/                 Unit tests (smoke + DB model tests)
└── integration/          Golden-path end-to-end tests
alembic/                  Database migrations
```

### Assessment Sections

| Section | Area | Questions |
|---------|------|-----------|
| A | AI Tools & General Literacy | 5 |
| B | Cybersecurity & AI Threats | 5 |
| C | Communication & Data Analytics | 5 |
| D | CCTV & Surveillance AI | 5 |

Scoring: 1=No experience, 3=Some experience, 5=Confident/Expert

Levels: avg < 2.5 = Beginner, avg < 3.75 = Intermediate, avg >= 3.75 = Advanced

## Tech Stack

- **Python 3.12** + **FastAPI** — web framework
- **PostgreSQL** — database
- **SQLAlchemy 2.0** — ORM
- **Alembic** — database migrations
- **Jinja2** — server-rendered templates
- **Pydantic Settings** — configuration management
- **Starlette SessionMiddleware** — cookie-based sessions
- **uv** — package management
