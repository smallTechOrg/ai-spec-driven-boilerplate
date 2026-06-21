# spec/ — the intention layer

The human-authored contract for this project. All code must match this spec; when they
disagree, spec wins — fix the code. The researcher authors it; the supervisor signs it
off. See [../harness/README.md](../harness/README.md) for the full SDD method.

```
spec/
  rules/        constraints — tech stack, code style, rule overrides
  features/     what the system should do — vision, architecture, capabilities
  patterns/     optional — reusable patterns the coding agent may apply
```

---

## rules/

Hard constraints for this project. The researcher fills these in at intake.

- [rules/tech-stack.md](rules/tech-stack.md) — language, framework, DB, deploy target
- [rules/code-style.md](rules/code-style.md) — style rules, framework gotchas

Any overrides to [harness/rules/](../harness/rules/) also live here.

## features/

One file per discrete request. Empty until work begins.

- **FR-NNN-title.md** — feature request, created during `/build`
- **CR-NNN-title.md** — change request, created during `/fix`

The researcher authors these; the supervisor signs them off before any code is written.

## patterns/

Lateral patterns — cross-cutting concerns that apply broadly across the system
(e.g. retry strategy, caching approach, observability conventions). Optional;
the coding agent adds these when a pattern emerges and is worth codifying.

---

## Governance

1. **Spec first** — no `src/` change without a backing spec change.
2. **One fact, one place** — never duplicate across files; cross-reference with links.
3. **`features/` = WHAT, `rules/` = HOW + constraints** — no implementation detail in features.
4. **Update spec before code** — if requirements change, spec changes first.
