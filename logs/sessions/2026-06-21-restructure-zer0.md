# Session — Restructure into Zer0

**Date:** 2026-06-21
**Branch:** `restructure/zer0`
**Goal:** Restructure the spec-driven boilerplate into **Zer0** — an academic,
open-source, four-layer coding-agent harness — keeping functionality, upgrading to
Claude Code's latest mechanisms (skills, sub-agents, workflows, hooks).

This file is both the build journal AND the resume point. Pick up exactly here.

---

## Locked decisions (from the design Q&A)

1. **Identity:** name = **Zer0** (zero-shot + śūnyatā/empty ground). Rename the GitHub
   repo to `zer0` (deferred — see Pending; local dir kept to avoid breaking the session).
2. **Four layers / philosophy:** `spec/`=goal, `src/`=action, `logs/`=outcome,
   `harness/`=mindfulness (the reconcile loop). `harness/` is the agent-agnostic source
   of truth; `.claude/` is a thin adapter. Claude Code only (dropped `.github/` + `AGENTS.md`).
3. **Roster (a real engineering team), 5 roles:**
   - `manager` = the **main session** (coordinates; not a sub-agent)
   - `designer` = PM + UX + spec author
   - `engineer` = feasibility + implementation
   - `qa` = reviewer + product-owner + end-user representative ("nothing gets past qa")
   - `analyst` = always-on observability + reconcile (reads logs/traces/tests/user prompts)
4. **Always-on:** every role holds a standing mandate, not a one-shot call; the analyst
   especially is continuously observing and decides when to act.
5. **Skills = invokable workflows:** `build`, `fix`, `deploy` (deploy is a later phase,
   default Render). No separate "reconcile" skill — that's the analyst's continuous job.
6. **Hook (mechanical enforcement):** push-after-every-commit only. The rest stay prose.
7. **Intake:** designer-led, **as many questions as needed, to the line level** — the
   user writes each spec line or answers a question that produces it. No placeholders.
   Gate to build = completeness checklist passes AND designer + engineer + qa sign off.
   Engineer reviews **each** spec draft for feasibility. (This supersedes the earlier
   "4 + optional 4" idea.)
8. **Specs are human-authored, harness-assisted** (designer drafts; human owns/edits).
9. **Phases:** designer derives per spec (no fixed model); ordered **user-value-first**.
10. **Stack default (in spec/engineering, editable):** Python + LangGraph + FastAPI /
    Next.js UI / SQLite (default) or DuckDB / Anthropic Claude / Render deploy later.
11. **Analyst output:** writes `logs/analysis/` reports AND may propose `spec/` amendments
    (never edits the goal silently).
12. **Delivery:** feature branch + PR (`restructure/zer0`).

---

## Done this session

- `harness/` — full source of truth: `README.md`, `philosophy.md`, `rules/` (5),
  `method/` (lifecycle, reconcile, layout), `roles/` (5), `workflows/` (5). *(committed)*
- `.claude/` adapter — `settings.json` (+ PostToolUse hook wiring),
  `hooks/push-after-commit.sh`, `rules/harness.md` (auto-load shim),
  `agents/` (designer, engineer, qa, analyst — thin pointers), `skills/` (build, fix,
  deploy — thin pointers).
- Removed: old `.claude/commands/*`, old `.claude/agents/*` (8), `AGENTS.md`, `.github/`,
  `spec/engineering/{ai-agents,phases,project-layout,spec-driven,secret-hygiene}.md`,
  `spec/engineering/workflows/`, `reports/`.
- Migrated method into `harness/`; rewrote `spec/engineering/{tech-stack,code-style}.md`
  as editable defaults; updated `spec/README.md`.
- Created `logs/` (sessions/runtime/analysis) + `logs/README.md`; created `src/` scaffold.
- Root `CLAUDE.md` + `README.md` rewritten for Zer0.
- `docs/zer0-deck.html` — deck of open questions + theory + recommended path.

---

## Pending / open (resume here)

- **Open design questions** — see `docs/zer0-deck.html` (the slide deck built for review):
  phase-model depth, how "always-on" maps to Claude Code's invoke model, MCP/`.mcp.json`,
  the spec-completeness checklist's exact items, `logs/runtime` schema, multi-CLAUDE.md
  for monorepos, and whether to package Zer0 as an installable plugin.
- **spec/product/ templates** still use the old `<!-- FILL IN -->` shape; review whether
  they need re-aligning to the Zer0 roles/loop language.
- **`preflight.sh` / `reset.sh`** at the root — left untouched; decide keep / move to
  `harness/scripts/` / drop.
- **GitHub repo rename → `zer0`** (`gh repo rename zer0`) — deferred to avoid breaking the
  live session's working directory + remote mid-flight. Do on merge.
- **`.env` is tracked-but-ignored locally**; `.venv/` present locally (git-ignored).
- Then: merge the PR, and the harness is ready for its first real `build`.

---

## Prompt log (high level)

- "Restructure into harness/src/spec/logs" → mapped to four-layer model.
- "Upgrade to skills; refactor piece by piece; ask lots" → switched to Q&A-driven design.
- "Academic standards; humans write specs; generate only what's needed; mindfulness model"
  → philosophy baked into `harness/`.
- Roster redefined as manager/designer/engineer/qa/analyst; skills = build/fix/deploy;
  intake = as many questions as needed (line level); name = Zer0; rename repo.
- "Going to sleep — leave a branch+PR and an HTML deck; ≤1 hour; resume exactly here."
