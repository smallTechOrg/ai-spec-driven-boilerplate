# Implementation Phases

Agents are built incrementally. Phasing is **requirements-driven**: the spec-writer derives the phases for your project from `spec/roadmap.md` — there is no fixed 1..N ladder and no fixed phase names. This file supplies the *model* (the two axes below and their gates); the authoritative per-project plan lives in `spec/roadmap.md` (`## Phases of Development`).

## Core Principle

**Ship the smallest user-testable win first. Then expand.**

Phase 1 is a thin but REAL vertical slice the user can test the first time, with zero rough edges on the tested path — never a models-only layer the user cannot exercise. Backend on the one core path is minimal but real (no fake data on the tested path); the frontend, built in parallel, is visually complete: real UI for the working path PLUS clearly-labelled non-functional stubs for everything coming later, so the user sees the vision. Each subsequent phase wires a stub into real functionality — one user-testable increment at a time.

## Two Axes of Every Build

Every build has two axes that meet in each phase:

- **Vertical axis — requirement-driven feature phases.** The *what* and *how many* phases. Derived bottom-up from `spec/roadmap.md`: each phase is one user-testable increment the requirements call for. There is no fixed ladder — a build emits only the phases its requirements need.
- **Horizontal axis — every slice carries.** The cross-cutting Definition of Done that rides *every* slice of *every* phase: README delta, observability, error handling, a real test, drift. These are **never their own late phases** — they ship *with* each feature, so they are never deferred past the point where the build stops.

The Vertical axis decides the *sequence*; the Horizontal axis is the *baseline* every step in that sequence must satisfy before its gate is green.

## The Vertical Axis — Requirement-Driven Feature Phases

The spec-writer carves the phases from the requirements. Two roles are fixed; everything else is emitted only when a requirement needs it.

### Phase 1 — Smallest User-Testable Win (thin real vertical slice)

Phase 1 is always the first phase, and it is always the **smallest first-time-right win**:

- One core path works end-to-end against the real LLM/API (keys from `.env`): the minimal domain types, data layer, and core logic that path needs — nothing more.
- Backend is minimal but REAL on that path — no fake data on what the user tests.
- Frontend (built in parallel) is visually complete: real UI for the one working path, PLUS clearly-labelled non-functional stubs for everything coming later. A stub must be visibly labelled so it is never mistaken for a bug.
- **Gate (all must pass):**
  1. `pyproject.toml` declares the DB driver in `[project.dependencies]` (e.g. `psycopg2-binary` for PostgreSQL) — never dev-only
  2. `uv run alembic upgrade head` succeeds against the configured database — this must be run and confirmed, not assumed
  3. The core path runs end-to-end against the real LLM/API; tests for the slice pass
  4. The Horizontal-axis Definition of Done is satisfied for every slice in this phase (see below) — proportionally: Phase 1 logs only its one real core operation, never gold-plated
  5. Working tree is clean and committed
  6. Phase test-handoff published; the human has tested the slice and approved (see Human Testing Gate)

### The real-provider gate (a role, not an ordinal)

The **real-provider gate** is the first phase whose core loop calls a **live provider** (LLM/API/search) end-to-end — often Phase 1 itself when the core path already hits the provider, otherwise the next phase that wires it in. From this gate onward:

- All external calls hit the real provider using keys loaded from `.env`; tests assert on real responses (shape/content), not hardcoded strings. A stub provider MAY remain as an optional offline fallback, but it is not required and the gate is NOT met by an all-stubbed run.
- **Gate (all must pass):**
  1. Agent runs end-to-end; at least one record written to DB; run status "completed"
  2. `pytest` passes against the **production DB driver** (e.g. PostgreSQL via psycopg2, not SQLite) **with** real LLM/API keys loaded from `.env`
  3. Tests are fully automated: `conftest.py` creates and tears down the test schema; no manual DB setup steps
  4. Real LLM/API keys are present in `.env` and the suite exercises the real provider — no all-stubbed run is accepted as the real-provider gate
  5. **Golden-path UI smoke test passes** (if the project has any UI or HTTP surface). Drives the full primary user flow through `TestClient` against the real LLM/API and asserts real response content (not only status codes). Edge-case and end-to-end UI assertions are required, not optional.
  6. **Live-server smoke:** the agent starts the app (`uv run python -m <pkg>`) and hits `/health` plus one real page with `curl`, exercising the live LLM/API path. Both return 200 and the page shows real AI output.

### Later feature phases (emitted only when a requirement needs them)

Each later phase wires a Phase-1 stub into real functionality — one user-testable increment at a time. The former fixed phases are now **feature phases the spec emits on demand**:

- **Secondary integrations / data sources** — a phase per integration the requirements call for; each runs for real, happy path end-to-end with real data.
- **API / CLI surface** — only if the spec calls for an external API or CLI.
- **UI** — only if `spec/ui.md` exists; implement the screens it specifies.

What used to be late phases — **error handling, observability, integration-test breadth, README/polish** — are **NOT phases**. They ride the Horizontal axis in every slice (below), so they are never stranded behind a stopping point.

## The Horizontal Axis — Every Slice Carries (Cross-Cutting Definition of Done)

Before any phase gate is green, **every slice in the phase** must satisfy this Definition of Done. This is what keeps README and observability from being deferred-forever:

1. **README delta (serialized, MANDATORY).** For every new command, setup step, env var, route, or capability this phase introduced, `README.md` is updated AND every README command in scope is actually run and confirmed to work from the stated directory. Because `README.md` is a **single shared file**, agent-builder applies the README delta as **one serialized step AFTER the phase's parallel slices land** — it is never written concurrently by fan-out slices, preserving the disjoint-paths invariant. A new command/route/capability with a stale README = BLOCKER.
2. **Observability (MANDATORY, proportional).** Every NEW operation this phase adds — LLM call, DB read/write, external HTTP request, agent graph node, API endpoint, CLI command — emits a structured log line through `src/<pkg>/observability/events.py` (structlog) carrying timestamp, level, trace/request id, and message (per `harness/patterns/engineering-practices.md`). qa-auditor scans the slice diff for new call-sites and requires a matching log emission; a new operation with no log line = BLOCKER. **Proportional:** Phase 1 logs only its one real core operation — full metrics/trace propagation grow per later phase. Never gold-plate the smallest-win slice.
3. **Error handling.** Every external call this phase adds (LLM/API/DB/HTTP) is wrapped with try/except + timeout (and retry where appropriate) and degrades gracefully — a non-critical failure does not crash the agent; error paths render human copy, not stack traces.
4. **Test.** The slice ships at least one real test asserting actual behaviour (response content / DB state), not just status codes; from the real-provider gate onward it runs against the real LLM/API (keys from `.env`) and the production DB driver (never SQLite-as-substitute).
5. **Drift (incremental).** Code matches `spec/roadmap.md` and the backing capability spec for the surfaces this phase touched — no silent drift introduced. (The whole-tree drift audit runs once at the Final Hand-off Gate.)

## Human Testing Gate

The build is autonomous WITHIN a phase, with a human testing gate BETWEEN phases — at EVERY phase boundary.

After a phase passes its automated gate and is committed, the build publishes a **test-handoff** and STOPS:
- The handoff gives exact run commands, what to click/look at, the expected result, and what is a labelled stub vs. real.
- Only the root session presents it and asks the human.
- The next phase starts ONLY after the human approves.
- On a reported issue → qa-auditor diagnoses and routes → the right generator (frontend and/or backend) fixes → re-gate → re-present.

## Parallel Slices Within a Phase

- spec-writer carves each phase into INDEPENDENT SLICES (the parallel units) with explicit dependencies; default to independence so slices build concurrently.
- agent-builder fans out a generator per slice — multiple code-generator AND code-generator invocations in a SINGLE message so they run concurrently (disjoint paths: frontend writes the frontend surface, backend writes `src/` — never the same file). Then fans out qa-auditor per slice concurrently and aggregates verdicts.
- Serialize ONLY across a true declared dependency. On a BLOCKED slice, loop only that slice's generator; other slices are unaffected. For headless/CLI builds, only backend generators run.

## Phase Gates

A phase is complete when ALL of the following are true:
1. All code for the phase is committed and pushed
2. All tests for the phase pass
3. Working tree is clean
4. Phase test-handoff published; (build) human tested and approved
5. qa-auditor sub-agent (or manual QA checklist) has signed off
6. For any phase that introduces the DB schema (the DB-scaffold phase): `alembic upgrade head` has been run against the real DB and succeeded
7. The Horizontal-axis Definition of Done is satisfied for every slice in this phase (README delta, observability log per new operation, error handling, a real test, incremental drift)

**Never mark a phase complete if any gate is red.**

**Never claim a phase passes based on tests alone if those tests use a different DB driver than production.** SQLite tests passing does not mean PostgreSQL migrations work.

**Never claim the real-provider gate (any phase whose core loop calls a live provider) passes on stubbed providers** — the gate runs against the real LLM/API with keys from `.env`.

## Phase Tracking

The current phase is recorded in git commit messages (`phase-N: [description]`). To see phase history, run `git log --oneline | grep "phase-"`.

## Adapting the Phases

Emit a phase only when a requirement needs that user-testable increment — the count and names come from `spec/roadmap.md`, not a fixed ladder. For example:
- A pure CLI build has no UI phase, because there is no UI requirement.
- A build with no database has a smaller First Win (no DB-scaffold work).
- A build with many integrations gets a phase per integration the requirements call for.

Observability, error-handling, README, and tests are **never separate phases** — they ride the Horizontal axis in every slice. Whatever the spec-writer decides, the core principle holds: **smallest user-testable win first**.

## Final Hand-off Gate (after the last phase)

After the final feature phase passes its gate, one whole-system gate runs before hand-off:

- **Whole-tree drift audit** (qa-auditor Mode B) — code matches the full spec; CLEAN before hand-off.
- **End-to-end integration sweep** — exercise the full system against real services, including edge cases, error paths, and any UI journey, so per-slice tests have not silently replaced system-level coverage.
- **README reviewed by the user; user accepts hand-off.**

---

## Language-Specific Gate Commands

The gate test command depends on the project language. The spec-writer sets the exact command per phase in `spec/roadmap.md` (## Phases of Development), honoring the test rules in `harness/patterns/tech-stack.md`.

| Language | DB-scaffold gate | Real-provider gate |
|----------|-------------|-------------|
| Python | `uv run alembic upgrade head` + `uv run pytest` | `uv run pytest` (PostgreSQL, automated via conftest) |
| TypeScript (Bun) | migration tool + `bun test tests/unit/` | `bun test tests/integration/` |
| TypeScript (Node) | migration tool + `npx vitest run tests/unit/` | `npx vitest run tests/integration/` |
| Go | `migrate up` + `go test ./internal/...` | `go test ./...` |

The real-provider gate runs with **real LLM/API keys loaded from `.env`** regardless of language; both the DB URL and the provider key(s) must be set.

## TypeScript/Bun Real-Provider Test Pattern

```typescript
// tests/integration/pipeline.test.ts
import { describe, it, expect, beforeEach } from "bun:test";

// Use the production DB driver via conftest-style setup/teardown — never SQLite-as-a-substitute
// Call the real LLM/API using keys from .env

describe("pipeline", () => {
  it("runs end-to-end against the real provider", async () => {
    // call runner against the real provider
    // assert DB record created with correct status
  });
});
```
