# Code Style (default — editable per project)

Part of the spec (the goal). The engineer follows it; the architect may amend it.

## Universal

- Clarity over cleverness. Match the surrounding code's idioms, naming, and structure.
- Small, single-purpose modules. No god-files. One concern per file.
- No dead code, no speculative abstractions, no commented-out blocks.
- Errors are handled, not swallowed. Every external call has a failure path.
- Types where the language supports them (Python hints, TS types).

## Python

- 3.12+, type-hinted. `ruff` for lint + format. `pydantic` for models & settings.
- Pure functions for tools/nodes: `(inputs) -> model`. Direct DB access (no repository
  pattern) unless the spec needs one.
- LLM behind a client wrapper; never call the provider SDK directly in business logic.

## TypeScript / Next.js

- Strict mode. Components small and typed. Data fetching at the edges, not in leaf
  components. Server/client boundaries explicit.

## Tests

- Test behavior, not implementation. Assert content, not just status codes.
- Against the production data store (see `tech-stack.md`), not a convenient substitute.
