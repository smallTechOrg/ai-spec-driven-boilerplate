# Implementation Phases

The planner derives phases from the spec. This file defines the default model — the
planner adapts it to the project. See [../../harness/process/README.md](../../harness/process/README.md).

## Core Principle

**Build the minimal working thing first, then expand.** A "working" agent in Phase 2
demonstrates the core loop end-to-end — even with stubs and no UI.

---

## Default Phase Model

### Phase 1 — Domain Models + Data Layer

Define core data types and DB schema. No business logic.

**Gate:**
1. DB driver is in `[project.dependencies]`, never dev-only
2. Migrations run (`alembic upgrade head` or equivalent) — confirmed, not assumed
3. Basic CRUD unit tests pass; working tree clean and pushed

### Phase 2 — Core Loop (Stubbed)

Implement the agent's main loop end-to-end with all external calls hardcoded as stubs.
Zero real API calls, zero network I/O.

**Gate:**
1. Agent runs end-to-end; at least one record written to DB; status "completed"
2. Tests pass against the production DB driver — not SQLite
3. Test setup is fully automated (no manual DB steps)
4. No LLM API key required to pass tests
5. Golden-path smoke test passes (if project has UI/HTTP) — asserts response content, not only status codes
6. Live-server smoke: app starts, `/health` + one real page return 200 via `curl`; exit codes in session report
7. Stub mode visibly labelled on every rendered page

### Phase 3 — First Real Integration

Replace the most critical stub with a real external call (usually the LLM or primary data source).

**Gate:** Happy path works with real data.

### Phase 4 — Error Handling + Resilience

Add error handling, retries, and timeouts to all external calls. Agent degrades gracefully.

**Gate:** All documented failure modes handled without crashing.

### Phase 5 — Remaining Integrations

Replace all remaining stubs. Agent runs fully end-to-end.

### Phase 6 — API / CLI Surface

Add the external API or CLI if the spec calls for it.

### Phase 7 — UI (if required)

Implement from `spec/features/ui.md`. Functional, not polished.

### Phase 8 — Integration Tests

Full-system integration tests pass reliably.

### Phase 9 — Observability + Logging

Structured logging and monitoring. Every major operation produces a log entry.

### Phase 10 — Polish + Handoff

Fix rough edges, update docs, final drift audit. README accurate. User accepts handoff.

---

## Phase Gate Checklist

A phase is complete when ALL are true:

- [ ] Code committed and pushed
- [ ] Gate test passes (run, output shown)
- [ ] Working tree clean
- [ ] Session report reflects the phase
- [ ] Reviewer has signed off

**Never mark a phase complete if any gate is red.**

## Language-Specific Gate Commands

The researcher/planner records the gate command in `spec/patterns/tech-stack.md`.

| Language | Phase 1 gate | Phase 2 gate |
|----------|-------------|-------------|
| Python + uv | `uv run alembic upgrade head` + `uv run pytest` | `uv run pytest` (production DB, automated via conftest) |
| TypeScript (Bun) | migration + `bun test tests/unit/` | `bun test tests/integration/` |
| TypeScript (Node) | migration + `npx vitest run tests/unit/` | `npx vitest run tests/integration/` |
| Go | `migrate up` + `go test ./internal/...` | `go test ./...` |

The Phase 2 gate must pass with **no LLM API key set**, regardless of language.

## Phase Tracking

Record the current phase in the session report and in commit messages (`phase-N: description`).
To see phase history: `git log --oneline | grep "phase-"`.
