# Zer0 — Claude Code entry point

This repo runs on **Zer0**, a four-layer coding-agent harness. Read this, then the
harness. Keep this file lean — the source of truth is `harness/`.

## First action, every session

1. Read `harness/README.md` and `harness/rules/non-negotiables.md`.
2. You are the **manager** (the main session). Your playbook: `harness/roles/manager.md`.
3. Check `spec/product/01-vision.md`. If it has `<!-- FILL IN -->`, intake isn't done —
   run the `build` skill (designer-led). Otherwise the spec is the goal; follow it.
4. Open/append a session report in `logs/sessions/` (`harness/workflows/session-report.md`).

## The four layers

| Folder     | Holds                              | Role owner   |
|------------|------------------------------------|--------------|
| `spec/`    | the goal                           | designer     |
| `src/`     | the action                         | engineer     |
| `logs/`    | the outcome                        | analyst      |
| `harness/` | mindfulness (keep the loop closed) | manager + qa |

`harness/` is the source of truth. `.claude/` is the thin adapter (agents, skills,
hooks, the rules shim). Don't duplicate harness content here — link to it.

## The team (delegate via sub-agents)

- `designer` — requirements, spec, UX (`harness/roles/designer.md`)
- `engineer` — feasibility, code (`harness/roles/engineer.md`)
- `qa` — standards, tests, sign-off (`harness/roles/qa.md`)
- `analyst` — always-on logs/reality + reconcile (`harness/roles/analyst.md`)

## Skills

- `build` — idea → working, reconciled system (`harness/workflows/build.md`)
- `fix` — diagnose + fix, loop kept closed (`harness/workflows/fix.md`)
- `deploy` — later phase, Render default (`harness/workflows/deploy.md`)

## Non-negotiables (full text: `harness/rules/non-negotiables.md`)

Spec before code · outcome is evidence (run the test) · docs must be true · commit then
push (hook-enforced) · never `git add -A` · app code on a feature branch via PR, never on
`main` · one phase at a time · close the loop before stopping · generate only what's needed.
