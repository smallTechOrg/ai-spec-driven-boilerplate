# Zer0

**Zer0 is a coding-agent harness** — a disciplined, agent-agnostic method for building
software with AI, where human intent and machine action stay continuously reconciled.
This repository is Zer0's Claude Code reference implementation.

Zero-shot from intent to a working system; the empty ground a build takes form from.

## The idea: four layers, one loop

| Layer      | Holds       | Question                    |
|------------|-------------|-----------------------------|
| `spec/`    | the goal    | what should it be?          |
| `src/`     | the action  | what is it?                 |
| `logs/`    | the outcome | what does it do?            |
| `harness/` | mindfulness | does outcome = goal? adjust |

```
spec → src → logs → (harness reconciles) → spec → …
```

A build isn't "done" when the code runs — it's done when the **outcome** (`logs/`)
matches the **goal** (`spec/`), and the harness can show they reconcile. See
`harness/philosophy.md`.

## The team

Zer0 runs like a small engineering team of always-on roles:

- **manager** (you, the main session) — coordinates, keeps the loop closing
- **designer** — turns your prompts into a complete spec; UX
- **engineer** — feasibility, then builds to the spec
- **qa** — standards + the end-user's goals; nothing ships without sign-off
- **analyst** — always watching logs, tests, and your prompts; feeds reality back

## Use it (Claude Code)

```bash
git clone <this repo> my-project && cd my-project
claude
```

Then:

```
/build an agent that <your idea>
```

The **designer** interviews you — for as long as it takes, to the line level — until
the spec is complete and the engineer confirms it's feasible. You sign off once; then it
builds, phase by phase, each gated by tests, with the analyst reconciling outcome against
goal. `/fix` for defects; `/deploy` when it's ready (Render by default).

## Layout

```
spec/      the goal     — human-authored intent (product/ + engineering/)
src/       the action   — the code
logs/      the outcome  — sessions/, runtime/, analysis/
harness/   the method   — rules/, method/, roles/, workflows/  (source of truth)
.claude/   the adapter  — agents, skills, hooks, rules shim
CLAUDE.md  entry point
```

## Default stack (editable)

Python + LangGraph + FastAPI · Next.js UI · SQLite/DuckDB · Anthropic Claude · Render
(deploy, later). Change it in `spec/engineering/tech-stack.md` — it's part of the goal,
not the harness.

## Status

This repository is the **Zer0 harness** itself. `main` stays harness-only; projects are
built on feature branches and reach `main` via reviewed PRs
(`harness/rules/non-negotiables.md`).

## Contributing

The contribution surface is the harness (rules, method, roles, workflows) and the
`.claude/` adapter. Generated application code is not.
