# Travel & Food Itinerary Agent

> **All commands run from the repo root.**

A Streamlit web app powered by Google Gemini. Enter a city → get the top 3 places to visit (with descriptions and opening hours/tips) plus 1 local dish to try.

Works fully offline in stub/demo mode when no API key is set — a visible banner tells you.

---

## Quick Start

### 1. Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (`pip install uv` or `irm https://astral.sh/uv/install.ps1 | iex` on Windows)

### 2. Install dependencies

```
# from repo root
uv sync --extra dev
```

### 3. Configure environment

```
# from repo root
cp .env.example .env
```

Edit `.env` and set your Google Gemini API key:

```
GOOGLE_API_KEY=your-key-here
TRAVEL_LLM_MODEL=gemini-2.5-flash
```

Leave `GOOGLE_API_KEY` blank to run in stub mode (no API key required for demo).

### 4. Run the app

```
# from repo root
uv run streamlit run src/travel_itinerary/app.py
```

Open http://localhost:8501 in your browser.

---

## Run Tests

```
# from repo root
uv run pytest tests/ -v
```

---

## Project Structure

```
src/travel_itinerary/
    app.py              ← Streamlit entry point
    config/settings.py  ← reads GOOGLE_API_KEY + TRAVEL_LLM_MODEL from env
    domain/models.py    ← Pydantic: Place, Dish, ItineraryResponse
    llm/
        client.py       ← LLMClient + create_client() factory
        providers.py    ← StubProvider (offline) + GeminiProvider (real)
tests/
    unit/               ← domain model + LLM client tests (no API key needed)
spec/                   ← product and engineering spec
```

---

## How It Works

1. User enters a city name in the Streamlit UI and clicks "Get Itinerary"
2. `LLMClient` builds a structured prompt and calls the configured provider
3. If `GOOGLE_API_KEY` is set: calls Google Gemini (`gemini-2.5-flash`)
4. If no key: returns hardcoded demo data with a visible stub banner
5. Response is parsed into Pydantic models and rendered as cards

---

## Stub Mode

When `GOOGLE_API_KEY` is not set, the app runs in stub mode:
- A yellow warning banner is shown on every page load
- Output is hardcoded demo data (not real AI responses)
- All tests pass without an API key



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
