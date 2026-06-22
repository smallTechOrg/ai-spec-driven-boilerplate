---
name: zero-shot-build
description: Turn a zero-shot idea into a perfectly-working, thoroughly-tested, spec-driven agent. One intake round (which also collects the API keys into .env), then the agent-builder runs the full team autonomously to a thoroughly-tested agent. Also used to add a new capability to an existing agent.
argument-hint: [your idea]
disable-model-invocation: true
allowed-tools: Bash(git*) Bash(gh*)
---

You run the only interactive step — intake — then hand off to the **agent-builder** orchestrator. The idea is in `$ARGUMENTS` (if empty, ask for it once). Goal: **one prompt → a perfectly-working, thoroughly-tested agent in ~20-30 minutes, with zero user interaction after intake.**

There is no build/approval gate. **Intake-only autonomy:** ask the upfront questions (and any needed clarifiers), collect the required API keys into `.env`, then let agent-builder run the team — design → scaffold → build → ship — to a thoroughly-tested agent with zero further interaction. Don't pause mid-build; agent-builder pauses only on a hard blocker (e.g. a required key still missing from `.env`).

## Stage 1 — Intake (the only interactive step)

Intake captures scope, stack, trigger, and constraints, MAY ask additional clarifying questions up front if anything is ambiguous, and asks the user to fill `.env` with the required API keys/secrets.

1. Acknowledge the idea in one sentence.
2. Load the question tool: `ToolSearch` with query `select:AskUserQuestion` (before asking).
3. Ask **one round** of questions via `AskUserQuestion` (add clarifiers if underspecified):
   - **MVP scope** — minimum to call it working?
   - **Stack** — language, database, hosting? ("no preference" → sensible defaults, documented as an assumption; no later user round to confirm).
   - **Output/trigger** — how invoked, what produced?
   - **Key constraints** — provider/API keys held, hard no's, compliance, systems to integrate.
4. **API keys.** Identify which provider/API keys the agent needs. Ask the user to fill `.env` (from `.env.example`) with the real keys/secrets — this is the only manual user step. The build and tests load these keys programmatically from `.env` (gitignored) and use them for all tests and evals; confirm keys by presence (bool) only — never echo, print, paste, or commit a secret value.
5. Synthesize answers into a one-paragraph brief. ("Just build it" → narrow MVP, Python + PostgreSQL defaults, documented as assumptions.)

## Stage 2 — Build (delegate, fully autonomous)

Invoke the **agent-builder** sub-agent once with the brief and the populated `.env`. Tell it to run design → scaffold → build → ship end-to-end, returning only the final report (it may note assumptions made; there is no design summary to approve). Each build phase must pass its gate — real-key tests + golden-path/live-server/UI smoke, plus edge-case and end-to-end coverage, against the production DB driver — before the next phase starts; "perfect, zero errors" before ship. Relay only the hard blockers it escalates (e.g. a required key still missing from `.env`).

## Stage 3 — Report

When agent-builder returns: summarize for the user what was built, how to run it (verified commands), what's deferred, and the PR link.

## Adding a capability to an existing agent

If the spec is already filled in and the user is adding a capability: skip the scope intake; confirm the existing `.env` already holds the needed keys and ask only if the new capability requires a new provider/key. Tell agent-builder to run spec-writer (add just the new `spec/capabilities/<name>.md` + update `index.md`, self-reviewed) → tech-architect (incremental phase) → the build loop. Same autonomy.
