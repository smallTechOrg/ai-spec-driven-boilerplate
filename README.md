# Construction Materials Sourcing Agent

> **All commands must be run from the repo root** (the directory containing `pyproject.toml`).

AI-powered sourcing agent for real estate and construction projects. Submit a materials list — bricks, cement, steel, sand, etc. — and receive ranked supplier recommendations scored by price, lead time, and quality certifications.

---

## Quick Start

### 1. Install dependencies

```
# repo root
uv sync
```

### 2. Configure environment

```
# repo root
cp .env.example .env
# Edit .env — set SA_DATABASE_URL and optionally SA_GEMINI_API_KEY
```

Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `SA_DATABASE_URL` | Yes | PostgreSQL connection string, e.g. `postgresql://user@localhost:5432/sourcing` |
| `SA_TEST_DATABASE_URL` | For tests | Separate test DB, e.g. `postgresql://user@localhost:5432/sourcing_test` |
| `SA_GEMINI_API_KEY` | No | Set to enable real AI sourcing via Google Gemini. Leave blank for stub mode. |
| `SA_LLM_MODEL` | No | Default: `gemini-2.5-flash` |
| `SA_LLM_PROVIDER` | No | Default: `auto` — real when key is set, stub otherwise |

### 3. Create databases

```
# repo root
psql -U your_user -c "CREATE DATABASE sourcing;"
psql -U your_user -c "CREATE DATABASE sourcing_test;"
```

### 4. Apply migrations

```
# repo root
uv run alembic upgrade head
uv run alembic current
```

`alembic current` must print a revision hash (e.g. `1f350cbaadde (head)`). Blank output means no migration was applied.

### 5. Run the server

```
# repo root
uv run python -m sourcing_agent
```

Open http://localhost:8001

---

## Using the Agent

1. Open the home page and fill in your project name.
2. Add one row per material: name, quantity, and unit (e.g. `Portland Cement / 500 / bags`).
3. Click **Start Sourcing**.
4. Watch the status page — it auto-polls until the run completes.
5. View the report: each material shows 3+ ranked suppliers scored by price (40%), lead time (35%), and certifications (25%).

### Stub mode vs. real mode

| Mode | How to activate | What happens |
|------|----------------|-------------|
| **Stub** | Leave `SA_GEMINI_API_KEY` blank | Returns simulated supplier data. A visible banner appears on every page. |
| **Real** | Set `SA_GEMINI_API_KEY` | Calls Google Gemini `gemini-2.5-flash` to research real suppliers. |

A yellow **"⚠ Running in stub mode"** banner is always visible when no key is set.

---

## Running Tests

Tests require `SA_TEST_DATABASE_URL` (or `SA_DATABASE_URL`) pointing at a PostgreSQL database. No LLM API key needed.

```
# repo root
uv run pytest
```

All 15 tests must pass. Run only unit or integration tests:

```
# repo root
uv run pytest tests/unit/
uv run pytest tests/integration/
```

---

## API Reference

### `POST /api/runs`
Create a sourcing run.

```json
{
  "project_name": "Downtown Tower",
  "materials": [
    {"name": "Portland Cement", "quantity": 500, "unit": "bags"},
    {"name": "Clay Bricks", "quantity": 10000, "unit": "units"}
  ]
}
```

Returns `{"run_id": "<uuid>", "status": "pending"}`.

### `GET /api/runs/{run_id}/status`
Poll run status: `pending | running | completed | failed`.

### `GET /api/runs/{run_id}/report`
Full recommendation report as JSON.

### `GET /health`
Health check. Returns `{"status": "ok"}`.

---

## Project Layout

```
src/sourcing_agent/
├── api/            # FastAPI routes + Jinja2 templates
├── config/         # Pydantic Settings (SA_ env prefix)
├── db/             # SQLAlchemy models, session, repository
├── domain/         # Pydantic domain models
├── graph/          # LangGraph agent (state, nodes, edges, runner)
└── llm/            # LLM provider abstraction (Gemini + Stub)
tests/
├── unit/           # DB repository + graph compile tests
└── integration/    # Full pipeline + golden-path UI smoke tests
alembic/            # Database migrations
spec/               # Product + engineering spec
```

---

## Scoring Formula

Each supplier is scored as:

    score = (1 - norm_price) x 0.40 + (1 - norm_lead_time) x 0.35 + min(1, certs/3) x 0.25

Where norm_price and norm_lead_time are normalised within each material's candidate set.
Rank 1 = highest score = recommended supplier.

Weights are configurable: `SA_WEIGHT_PRICE`, `SA_WEIGHT_LEAD_TIME`, `SA_WEIGHT_CERTS`.

---

## What's Next (Phase 3+)

- **Phase 3:** Real Gemini integration — live supplier research
- **Phase 4:** Error handling + resilience
- **Future:** RFQ generation, supplier CRM, PDF/Excel export, multi-user auth

---

## What This Is

A starting point for anyone who wants to build an AI agent without writing boilerplate from scratch. The repo ships with:

- A structured **spec template** covering product vision, architecture, capabilities, data model, API, and UI
- An **agent-builder** sub-agent that orchestrates the full build lifecycle
- Sub-agents for spec writing, reviewing, tech design, planning, and auditing
- Engineering rules baked into the spec so every AI coding session is consistent
- Phase-gated implementation — minimal working thing first, then iterative expansion

---

## How to Use This

### Step 1 — Clone and configure

```bash
git clone https://github.com/smallTechOrg/ai-spec-driven-boilerplate.git my-agent
cd my-agent
cp .env.example .env
```

### Step 2 — Open in Claude Code (or any AI coding assistant)

```bash
claude
```

### Step 3 — Kick off the agent builder with your idea

```
/build I want an agent that monitors my Shopify store for low-inventory products and automatically drafts restock emails to suppliers
```

Or just describe your idea naturally — the agent-builder will take it from there.

---

## What Happens Next (Fully Automated)

The **agent-builder** orchestrates this sequence:

```
Your idea
    ↓
[spec-writer]     → Asks clarifying questions → Drafts product spec
    ↓
[spec-reviewer]   → Checks coherence, flags gaps → Requests revisions
    ↓
[spec-writer]     → Iterates until spec is complete
    ↓
[tech-designer]   → Proposes tech stack, architecture, data model
    ↓
You approve the spec & tech design
    ↓
[planner]         → Breaks work into phases (minimal → complete)
    ↓
[plan-reviewer]   → Validates plan against spec
    ↓
Phase 1: Build the minimal working agent (core loop, no polish)
    ↓
[qa-auditor]      → Tests phase 1
    ↓
Phase 2, 3, ... : Iterate and expand
    ↓
[drift-auditor]   → Ensures code matches spec throughout
    ↓
Hand-off to you
```

**Nothing is skipped.** If a phase fails QA, it stays in that phase until it passes.

---

## Development Phases (Default Model)

| Phase | What Gets Built |
|-------|-----------------|
| 1 | Domain models + data layer |
| 2 | Core agent loop (no integrations, stubbed tools) |
| 3 | First real integration (the "happy path" end-to-end) |
| 4 | Error handling, retries, resilience |
| 5 | Remaining integrations |
| 6 | API / CLI surface |
| 7 | Basic UI (if needed) |
| 8 | Integration tests |
| 9 | Observability + logging |
| 10 | Polish, documentation, hand-off |

Each phase ends with a commit and passes QA before the next phase begins.

---

## Repo Layout

```
.claude/
  agents/           ← Sub-agents (agent-builder, spec-writer, etc.)
  commands/         ← Slash commands (/build, /spec-check, /plan)
.github/
  copilot-instructions.md  ← Global Copilot instructions (mandatory spec reads)
  agents/           ← Copilot agent mode definitions (drift-auditor, planner, etc.)
  prompts/          ← Slash-style Copilot prompts (/plan, /challenge, /spec-check)
  instructions/     ← Scoped auto-applied rules (code-style, secret-hygiene, etc.)
spec/
  product/          ← What your agent does (fill this in or let spec-writer do it)
  engineering/      ← How AI agents should write code for this project (immutable rules)
    workflows/      ← Step-by-step procedures for each agent/workflow type
reports/
  sessions/         ← Auto-generated session logs from every AI coding session
CLAUDE.md           ← Entry point for Claude Code
AGENTS.md           ← Entry point for OpenAI Codex / GitHub Copilot
.env.example        ← Environment variable template
```

---

## Manually Editing the Spec

If you prefer to write the spec yourself before involving AI:

1. Open `spec/product/01-vision.md` and fill in the placeholders
2. Work through each file in `spec/product/` in order
3. Once the spec is complete, run `/plan` to jump straight to the planning phase

---

## Rules That AI Agents Follow

Every AI session in this repo follows the rules in `spec/engineering/ai-agents.md`:

- Read the full spec before writing any code
- Open a session report at `reports/sessions/`
- Commit every logical unit of work (never accumulate uncommitted changes)
- One phase at a time — no skipping
- Write tests before marking a phase complete
- Update this README whenever the project layout changes

---

## FAQ

**Can I use this without Claude Code?**
Yes. `AGENTS.md` has the same entry point for OpenAI Codex and GitHub Copilot. The sub-agents are plain markdown files.

**What if my agent needs a database?**
The spec template includes a data model section. The tech-designer sub-agent will recommend the right database for your use case.

**What if I already have a tech stack in mind?**
Tell the agent-builder upfront: `/build [idea] — use Python + FastAPI + PostgreSQL`. It will skip the tech design Q&A for those decisions.

**What if something breaks?**
Each phase is resilient by design. The QA auditor will catch failures before the next phase starts. You can always re-run a phase.

---

## Test-Branch Workflow

The recommended way to iterate on this boilerplate:

1. Keep `main` as the clean boilerplate — only spec, engineering rules, and agent config.
2. For each build attempt, create a numbered test branch: `test-1`, `test-2`, etc.
3. Give the agent-builder a single-line prompt on the test branch. Let it build.
4. Review and test the result on that branch.
5. **Never merge the generated application code back to main.** Test branches are disposable.
6. If a run surfaces a boilerplate improvement (a clearer spec template, a missing rule), cherry-pick or manually apply that fix to `main`.

---

## Contributing

This is a boilerplate, not a framework. Improvements to the spec templates, engineering rules, agent definitions, or workflow specs belong on `main`. Generated application code does not.
