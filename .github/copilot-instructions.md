# GitHub Copilot — AI Agent Boilerplate

All rules are in [`spec/engineering/ai-agents.md`](../spec/engineering/ai-agents.md). Read that first.

## Mandatory spec reads — every session

Before responding to any coding task, you **must** have read every file listed
in [`instructions/spec-files.instructions.md`](instructions/spec-files.instructions.md)
in full during the current session — from disk, not from a summary or conversation history.

A summarised spec is **not** a spec. If your context window holds only a paraphrase of a spec file, re-read it.

## Intake/approval UI (canonical rule)

For all user-facing intake and approval steps, always use a dynamic question UI (e.g., Copilot's `askQuestions`, Claude's UI tools). Only fall back to plain chat if no UI tool exists. Never ask intake or approval questions via plain chat unless absolutely necessary.

After intake and initial approval, proceed autonomously through all workflow phases. Do not pause or wait for user input between phases unless a true blocker is encountered or the user explicitly requests a pause.

## Copilot-specific

Scoped instructions in [`instructions/`](instructions/) auto-apply to matching paths via `applyTo` frontmatter — each is a thin pointer to a `spec/engineering/` file.

## Agents (invoke via `@<name>`)

| Agent | Purpose |
| ----- | ------- |
| `drift-auditor` | Audit spec/code drift |
| `dry-auditor` | Audit for duplicated facts |
| `link-validator` | Validate markdown links |
| `planner` | Draft a plan before multi-file edits |
| `plan-reviewer` | Review a plan before executing |
| `spec-reviewer` | Verify a change traces back to spec |

## Slash commands

| Command | Purpose |
| ------- | ------- |
| `/plan` | Dispatch planner for a described task |
| `/spec-check` | Dispatch drift-auditor |
| `/spec-new-capability` | Scaffold a new capability spec |
| `/challenge` | Grill the pending change before approval |
