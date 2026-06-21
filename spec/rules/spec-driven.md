# Spec-Driven Development — project rules

The method is defined in [harness/rules/spec-driven.md](../../harness/rules/spec-driven.md).
This file records project-specific extensions.

---

## What goes where in this project

| Spec file | Holds |
|-----------|-------|
| `spec/features/` | WHAT — behavior, data, API surface, UI, agent graph |
| `spec/patterns/` | HOW — tech stack, code style, framework choices |
| `spec/rules/` | CONSTRAINTS — rules, phases, hygiene |

## Adding a new capability

1. Add a file to `spec/features/capabilities/`
2. Get supervisor sign-off
3. Then write the code

Do not add capabilities by writing code and describing it after.

## When spec and code disagree

Spec wins. Fix the code. If the spec was wrong, update the spec first (get sign-off),
then fix the code.
