# Code Style

> **Boilerplate status:** The tech-designer sub-agent fills in the language-specific sections. General rules below apply to all projects.

---

## Universal Rules

These apply regardless of language or framework:

1. **Types at boundaries** — every function that crosses a module boundary must use typed inputs and outputs (Pydantic, TypeScript interfaces, Go structs, etc.) — never raw dicts or `any`
2. **One responsibility per file** — a file does one thing; if it's doing two things, split it
3. **No comments explaining WHAT** — code should be self-documenting via names; only comment WHY something non-obvious is done
4. **No dead code** — remove unused imports, functions, and variables immediately; don't comment them out
5. **Fail loudly at startup** — validate all required config/env vars at startup; don't fail silently at runtime
6. **No hardcoding** — values that could change (URLs, limits, credentials) go in config or environment variables

## Naming Conventions

<!-- FILL IN: Filled in by tech-designer based on language choice. -->

## File Organization

<!-- FILL IN: Filled in by tech-designer. How are files grouped — by layer, by feature, by type? -->

## Error Handling Pattern

<!-- FILL IN: Filled in by tech-designer. How are errors represented and propagated? -->

## Logging Pattern

<!-- FILL IN: Filled in by tech-designer. Structured vs. unstructured? What fields are always included? -->

## Testing Conventions

<!-- FILL IN: Filled in by tech-designer. Unit test location, naming, runner. -->

## What NOT to Do

<!-- FILL IN: Anti-patterns specific to this tech stack. Filled in by tech-designer. -->
