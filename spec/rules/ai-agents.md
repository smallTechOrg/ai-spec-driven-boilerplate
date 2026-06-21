# AI Agent Rules — project extension

Universal rules live in [harness/rules/](../../harness/rules/). This file adds
project-specific extensions and a session checklist with correct paths.

---

## Session Start Checklist

Complete in order before writing any code:

- [ ] Read `harness/rules/non-negotiables.md`
- [ ] Check `spec/features/vision.md` — if it still has `<!-- FILL IN -->`, run `/build`
- [ ] Check the latest session report in `logs/sessions/` (SessionStart hook surfaces it)
- [ ] `git status` — working tree must be clean
- [ ] Confirm you are on a feature branch, not `main`

## Gate Law

```
INTAKE  ─▶  SPEC  ─▶  ONE APPROVAL  ─▶  BUILD (phase by phase, gated by tests)
```

- Stack decisions belong to the user — captured at intake, never chosen autonomously
- No code before the single approval gate clears
- Each phase passes its gate before the next starts
- See [../rules/phases.md](phases.md) for phase definitions

## Closing a Session

- [ ] Working tree clean (all changes committed and pushed)
- [ ] Session report up to date with what was done and what's next
- [ ] Tests pass
- [ ] README updated if setup steps or commands changed
