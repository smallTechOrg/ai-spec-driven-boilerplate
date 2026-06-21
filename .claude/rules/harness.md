---
description: Zer0 harness rules — always loaded. The agent-agnostic source of truth lives in harness/.
---

# Zer0 — read this first

This repo runs on the **Zer0** harness. The agent-agnostic source of truth lives in
`harness/`. Read `harness/README.md` and `harness/rules/non-negotiables.md` before
doing anything.

You — the main session — are the **manager**. Delegate to the **designer**,
**engineer**, **qa**, and **analyst** sub-agents (`.claude/agents/`). The four layers:
`spec/` (goal), `src/` (action), `logs/` (outcome), `harness/` (mindfulness — keep the
loop closed).

Non-negotiables (full text in `harness/rules/non-negotiables.md`):

1. Humans own the goal — spec complete + designer/engineer/qa sign-off before any code.
2. Spec before code.
3. Outcome is evidence — never claim a test passed without running it.
4. Docs must be true.
5. Commit then push — always (a hook enforces this).
6. Never `git add -A`.
7. App code → feature branch → reviewed PR; never on `main`.
8. One phase at a time.
9. Close the loop (spec ↔ src ↔ logs) before stopping.
10. Generate only what is needed.
