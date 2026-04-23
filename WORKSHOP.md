# Workshop Guide — Building AI Agents in 10 Minutes

This guide is for workshop facilitators and participants. It covers setup, the demo flow, and how to iterate quickly.

---

## Before the Workshop (Do This Once)

### 1. Prerequisites

| Tool | Install |
|------|---------|
| Python 3.12+ | `brew install python` or [python.org](https://python.org) |
| uv | `curl -Lsf https://astral.sh/uv/install.sh \| sh` |
| Claude Code CLI | `npm install -g @anthropic/claude-code` |
| git | pre-installed on most systems |

### 2. Clone the boilerplate

```bash
git clone https://github.com/smallTechOrg/ai-spec-driven-boilerplate.git my-agent
cd my-agent
cp .env.example .env
```

### 3. Get API keys

| Key | Where to get it | Required? |
|-----|----------------|-----------|
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) | Yes (for real LLM calls) |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) | No (topic search degrades gracefully) |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | For Claude Code CLI |

Edit `.env` and fill them in.

### 4. Install dependencies

```bash
uv sync
```

### 5. Run pre-flight check

```bash
./preflight.sh
```

All green → ready. Fix anything red before the workshop.

---

## The Demo Flow (~10 minutes)

### Step 1 — Open Claude Code in the repo

```bash
claude
```

### Step 2 — Give your first prompt

```
/build [describe your agent idea, include tech preferences if you have them]
```

**Good first prompts include:**
- What the agent does (one sentence)
- Tech preferences: `Python, PostgreSQL` or `TypeScript, no DB`
- Key integrations you have API keys for

Examples:
```
/build Monitor my GitHub repos for stale PRs (>3 days old) and post Slack reminders — Python, PostgreSQL, I have a Slack webhook URL
```
```
/build Daily email digest: pull my top 5 RSS feeds, summarize with AI, send at 8am — Python, no database needed, I have ANTHROPIC_API_KEY and SendGrid
```

### Step 3 — Answer 4 questions

The agent-builder asks exactly 4 questions:
1. MVP scope (narrow skeleton vs. full vision)
2. Stack (language, database, hosting)
3. Output/trigger (how it runs, what it produces)
4. Constraints (API keys, things to avoid)

Answer them. Takes ~2 minutes.

### Step 4 — Approve once

You'll see a single summary: scope, stack, 2-phase build plan. Say "Start building."

### Step 5 — Watch it build

- Phase 1: domain models + DB schema → tests pass
- Phase 2: stubbed agent loop → end-to-end test passes

~8 minutes total. You have a running skeleton.

---

## Iterating New Versions

After the skeleton is running, each iteration adds one real capability:

```
"Replace the stub post generation with a real Gemini call"
```
→ One phase, ~10 minutes, committed and tested.

```
"Add the web dashboard with a trigger button"
```
→ One phase, ~10 minutes.

This is the loop. Each version is demoed, committed, and working before moving to the next.

---

## If Something Goes Wrong

| Problem | Fix |
|---------|-----|
| `AskUserQuestion` tool not available | Claude Code will ask questions in plain text instead — answer in the chat |
| Tests fail at Phase 1 | Usually a missing env var or `data/` dir — run `./preflight.sh` |
| DB connection error | Check `DATABASE_URL` in `.env`; for SQLite, ensure `data/` exists |
| Import error on startup | Run `uv sync` to install missing packages |
| LLM call fails in Phase 3+ | Stub mode still works — skeleton runs without API keys |

---

## Tips for a Smooth Demo

1. **Run `./preflight.sh` right before** — catches issues in 5 seconds
2. **Pre-type your first prompt** — have it ready to paste, don't type it live
3. **Pick an idea with 2–3 clear outputs** — avoids ambiguity in the intake questions
4. **Include tech preferences in the first prompt** — saves one question round
5. **The skeleton runs without real API keys** — Phase 1+2 are always stubs; demo the flow, swap real calls in later iterations
