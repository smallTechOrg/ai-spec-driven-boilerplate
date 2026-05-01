# Food Tracker

Upload a food photo in your browser and get an instant calorie + macro breakdown. Powered by Google Gemini Vision.

> **All commands run from the repo root** (`ai-spec-driven-boilerplate/`).

---

## Quick Start

### 1. Install dependencies

```sh
uv sync --extra dev
```

### 2. Create your `.env` file

```sh
cp .env.example .env
```

Edit `.env` and set at minimum:

```
FOOD_TRACKER_DATABASE_URL=postgresql://localhost/food_tracker
FOOD_TRACKER_GEMINI_API_KEY=<your Google Gemini API key>
```

Leave `FOOD_TRACKER_GEMINI_API_KEY` blank to run in **stub/demo mode** — every analysis returns hardcoded data and a visible warning banner. No API key needed for testing.

### 3. Create the databases

```sh
createdb food_tracker
createdb food_tracker_test
```

### 4. Run migrations

```sh
uv run alembic upgrade head
uv run alembic current
```

The second command should print the revision ID (e.g. `ba88f74aeae7 (head)`). Blank output = silent failure — check your `FOOD_TRACKER_DATABASE_URL`.

### 5. Start the server

```sh
uv run python -m food_tracker
```

Open [http://localhost:8001](http://localhost:8001).

---

## Usage

1. Go to [http://localhost:8001](http://localhost:8001)
2. Select a JPEG, PNG, or HEIC food photo (max 10 MB)
3. Click **Analyse**
4. See food name, calories, protein, carbs, and fat

---

## Running Tests

```sh
TEST_DATABASE_URL=postgresql://localhost/food_tracker_test \
FOOD_TRACKER_DATABASE_URL=postgresql://localhost/food_tracker_test \
uv run pytest tests/ -v
```

All 15 tests pass. No API key needed.

### Live Gemini test (optional — requires your API key)

```sh
FOOD_TRACKER_GEMINI_API_KEY=<your-key> \
FOOD_TRACKER_DATABASE_URL=postgresql://localhost/food_tracker_test \
uv run pytest tests/integration/test_gemini_live.py -v
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FOOD_TRACKER_DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `FOOD_TRACKER_GEMINI_API_KEY` | No | — | Gemini key. Absent = stub/demo mode |
| `FOOD_TRACKER_LLM_MODEL` | No | `gemini-2.0-flash` | Gemini model name |
| `FOOD_TRACKER_PORT` | No | `8001` | HTTP port |
| `TEST_DATABASE_URL` | No | `postgresql://localhost/food_tracker_test` | Used by pytest |

---

## Project Structure

```
src/food_tracker/
  api/          FastAPI routes + app factory
  config/       Settings (Pydantic BaseSettings)
  db/           SQLAlchemy models + session
  domain/       Pydantic domain models
  graph/        Pipeline state, nodes, runner
  llm/          LLM provider abstraction (Gemini + Stub)
  observability/ Structured logging
  templates/    Jinja2 HTML templates
tests/
  unit/         No DB, no network
  integration/  Real PostgreSQL, stub LLM (or live Gemini)
alembic/        DB migrations
spec/           Product + engineering spec
reports/        Session reports + implementation plan
```

---

## Deferred / Future

- Micronutrient breakdown (vitamins, minerals, sodium)
- Daily totals dashboard and history
- User authentication
- Barcode / label scanning

---

---

# AI Agent Boilerplate — Spec-Driven, Zero-Shot to Working Agent

This is a boilerplate for building AI agents spec-first. Give it a one-line idea. Walk away with a working, tested, phased agent.

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
