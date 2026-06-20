# Customer-Support Triage Agent

Paste an incoming support ticket and get back, in one step: an **urgency** label, a **category** label, and a
**drafted suggested reply** to the customer — grounded in your support policies, not invented. Built from the
spec-driven harness in this repo (`harness/`): every acceptance criterion is bound to an executable check, and
"done" means the agent booted over HTTP and gave the right answer (the gate exits 0).

## What it does

- **Triage (the real v1 capability):** classify a ticket's urgency (`low` / `normal` / `high` / `urgent`) and
  category (`billing` / `technical` / `account` / `shipping` / `general`), then draft a reply that
  acknowledges the issue and states the next step. The agent calls `classify_ticket` for the routing decision
  and `search_policy` to ground any timeframe before drafting — it never invents a policy, and it refuses to
  perform irreversible actions (it drafts the reply, but a refund/deletion must be done by an authorized human).
- **Escalate** (P2) and **Summarize thread** (P3) ship as deterministic, journey-complete **stubs** — wired in
  and reachable, returning a fixed contract until promoted via `/spec-new-capability`.

## Prerequisites

- Python 3.12, [`uv`](https://docs.astral.sh/uv/), Node 20+ (for the UI), `jq` (for the gate script).
- A funded LLM API key. Default provider is Anthropic, default model `claude-haiku-4-5` (cheap tier).

## Setup

```bash
cp .env.example .env          # then edit .env and set APP_LLM_API_KEY=<your funded key>
uv sync                       # install pinned Python deps (see pyproject.toml)
make setup                    # install the UI deps + the Playwright chromium browser
```

`.env` keys (read via pydantic-settings, prefix `APP_`):

| Key | Default | Notes |
|-----|---------|-------|
| `APP_LLM_API_KEY` | (none — **required**) | your funded key; `.env` is gitignored, never commit it |
| `APP_LLM_PROVIDER` | `anthropic` | `anthropic` / `openai` / `google_genai` |
| `APP_LLM_MODEL` | `claude-haiku-4-5` | cheap tier; switch tiers with this var, no code change |
| `APP_DATABASE_URL` | `sqlite+aiosqlite:///./agent.db` | local SQLite; Postgres (`asyncpg`) at deploy |
| `APP_PORT` | `8001` | backend port |

## Run it

```bash
make dev                      # starts the backend AND the UI together (Ctrl-C kills both)
```

- Backend + API: <http://localhost:8001>
- Observability dashboard (every run in plain English — what it did, whether it worked, what it cost):
  <http://localhost:8001/traces>
- UI: <http://localhost:3001>

Triage a ticket over the API directly:

```bash
curl -s -X POST http://localhost:8001/runs \
  -H 'content-type: application/json' \
  -d '{"goal":"Triage this ticket and draft a reply: I was charged twice for my subscription and want a refund."}' | jq
```

## The gate — the mechanical definition of done

```bash
make gate                     # the whole DEMO suite; a real APP_LLM_API_KEY is required
echo $?                       # 0 = done. Anything else = not done.
```

`make gate` runs: the `[@eval]` binding lint, the full `uv run pytest` suite (FakeModel loop tests + the
judge outcome test + the Playwright UI journey), then boots the real server on port 8001, checks `/health`,
runs a **two-turn** conversation over HTTP, runs the **judge-stable outcome eval** (a 200 with a wrong answer
fails), drives the UI in a real browser, and confirms the run is visible at `/traces`.

> The keyless checks (structure, imports, the `[@eval]` lint, the FakeModel unit/contract tests) run without a
> key. The full `make gate` — which boots the real agent and runs the live LLM judge — needs a funded
> `APP_LLM_API_KEY`. **Running `make gate` end to end with your key is the owner's manual step.**

## Layout

- `agent/` — the agent package (config, llm, db, domain, tools, graph, runner, server, evals, gate harness).
- `spec/` — the spec contract (product, capabilities with EARS criteria, agent layer ledger, tech stack).
- `tests/` — the deterministic test pyramid + `tests/e2e/` Playwright journey.
- `ui/` — the Next.js primary-journey page.
- `Makefile`, `scripts/demo_gate.sh` — the gate entry points.
- `harness/` — the spec-driven harness that generated this agent (the recipes + workflows + gates).
