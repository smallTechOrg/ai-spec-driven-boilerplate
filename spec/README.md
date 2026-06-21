# spec/ — the intention layer

The human-authored contract for this project. All code must match this spec; when they
disagree, spec wins — fix the code. The researcher authors it; the supervisor signs it
off. See [../harness/README.md](../harness/README.md) for the full SDD method.

```
spec/
  rules/        project-specific rule extensions (on top of harness/rules/)
  features/     what the system should do — vision, architecture, capabilities
  patterns/     how to build it — tech stack, code style, framework choices
```

---

## rules/

Project-specific extensions and overrides on top of
[harness/rules/](../harness/rules/). Harness rules apply universally; rules here
narrow or extend them for this project.

- [rules/ai-agents.md](rules/ai-agents.md) — project-level AI session rules
- [rules/phases.md](rules/phases.md) — phased build model for this project
- [rules/spec-driven.md](rules/spec-driven.md) — spec-first discipline (project-specific)
- [rules/secret-hygiene.md](rules/secret-hygiene.md) — secrets handling (project-specific)

## features/

What the system should be. The researcher fills these in; they are the source of truth
for product intent. Code conforms to features, never the reverse.

- [features/vision.md](features/vision.md) — purpose, goals, success criteria
- [features/architecture.md](features/architecture.md) — system design, layers, data flow
- [features/capabilities/](features/capabilities/) — one file per discrete capability
- [features/data-model.md](features/data-model.md) — data schema
- [features/api.md](features/api.md) — API surface
- [features/ui.md](features/ui.md) — UI requirements
- [features/agent-graph.md](features/agent-graph.md) — agent graph (LangGraph/etc. projects)

## patterns/

How to build it — stack choices, code conventions, framework-specific rules. These are
project-specific; the generic and agentic patterns live in
[harness/patterns/](../harness/patterns/).

- [patterns/tech-stack.md](patterns/tech-stack.md) — language, framework, DB, deploy target
- [patterns/code-style.md](patterns/code-style.md) — style rules, framework gotchas

---

## Governance

1. **Spec first** — no `src/` change without a backing spec change.
2. **One fact, one place** — never duplicate across files; cross-reference with links.
3. **Features are atomic** — each file in `capabilities/` describes one discrete thing.
4. **`features/` = WHAT, `patterns/` = HOW** — no implementation detail in features.
5. **Update spec before code** — if requirements change, spec changes first.
