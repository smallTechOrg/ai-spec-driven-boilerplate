# Implementation Phases

Agents are built incrementally. This is the default model; the planner sub-agent adapts it per project.

**Core principle: build the minimal working thing first, then expand.** A "working" agent in Phase 2
demonstrates the core loop end-to-end — even with stubbed connections, hardcoded data, and no UI. Each
later phase makes it more real.

The **raised baseline** ([`agentic-architecture.md`](agentic-architecture.md)) means that "minimal
working thing" now includes the core agentic layers — working/short-term memory, one MCP tool,
retrieval wiring, and an eval-harness skeleton — all stubbed and offline at Phase 2. The earns-its-place
layers (long-term memory, real retrieval, multi-agent, HITL, durable execution) land in later phases,
each only when the spec needs it.

---

## Default phase model

### Phase 1 — Domain Models + Data Layer
Define all core data types; set up the DB schema. No business logic yet. The schema includes the
baseline agentic entities (`runs`, `messages`, `memory_records`, an embeddings/vector table,
`eval_results` — see `../product/04-data-model.md`) plus the agent's domain entities.
**Gate:** (1) `pyproject.toml` declares the DB driver in `[project.dependencies]`, never dev-only;
(2) `uv run alembic upgrade head` succeeds against the configured DB and `uv run alembic current` shows a
revision — run and confirmed, not assumed; (3) CRUD unit tests pass; (4) tree clean and committed.

### Phase 2 — Core Agent Loop (Stubbed)
Implement the agent's full loop start to finish. **All external calls are hardcoded stubs — zero real
API calls, zero network I/O.** The agent runs fully offline; if `pytest` needs an API key, Phase 2 isn't
done.
**Gate:**
1. Agent runs end-to-end; ≥1 record written to DB; run status `completed`.
2. `pytest` passes against the production DB driver (→ [`tech-stack.md`](tech-stack.md) § Database & Tests),
   fully automated via `conftest.py`, **no LLM API key required**.
3. **Golden-path UI smoke test passes** (if any UI/HTTP surface) — asserts rendered content, not just
   status codes. → [`workflows/golden-path-smoke-test.md`](workflows/golden-path-smoke-test.md).
4. **Live-server smoke:** start the app (`uv run python -m <pkg>`), hit `/health` + one real page with
   `curl`, both 200; log exit codes in the session report.
5. **Stub mode is visibly labelled** on every page. → [`patterns/llm-providers.md`](patterns/llm-providers.md).
6. **For ReAct agents:** the stub simulates ≥2 iterations (one action, then `FINAL ANSWER:`), and a test
   drives the loop past `max_agent_iterations` into `force_finalize` (best-effort answer, not a hard
   failure). Observability baseline holds — structured per-`run_id` logs, token/cost on the run, and the
   `action_history` trace surfaced to the user. → [`patterns/react-agent.md`](patterns/react-agent.md).
7. **Baseline agentic layers wired (stubbed):**
   - **Memory** — working + short-term; context assembled in one place. → [`patterns/memory-and-context.md`](patterns/memory-and-context.md).
   - **Tools/MCP** — ≥1 MCP tool behind the action-safety boundary, stub returns a deterministic typed result. → [`patterns/tools-and-mcp.md`](patterns/tools-and-mcp.md).
   - **Retrieval** — embeddings + vector store wired with deterministic fake vectors. → [`patterns/retrieval.md`](patterns/retrieval.md).
   - **Evals** — an eval-harness skeleton (tiny fixed dataset + ≥1 assertion) runs in CI against the stub. → [`patterns/observability-and-evals.md`](patterns/observability-and-evals.md).

### Phase 3 — First Real Integration
Replace the most critical stub (usually the LLM, the primary data source, or the first real MCP server)
with a real call. **Gate:** happy path works with real data.

### Phase 4 — Error Handling + Resilience
Add try/catch, retries, timeouts to all external calls; degrade rather than crash on non-critical
failures. **Gate:** all documented failure modes handled without crashing.

### Phase 5 — Remaining Integrations
Replace remaining stubs. **Gate:** all integrations real; full end-to-end run.

### Phase 6 — API / CLI Surface
Add the external API or CLI if the spec calls for it. **Gate:** all specified endpoints/commands work.

### Phase 7 — Basic UI (if required)
Implement the UI from `spec/product/06-ui.md` — functional, not polished.
**Gate:** all specified screens present and functional; any client-rendered content (charts, SPA, htmx,
streamed updates) covered by a **browser-level test** asserting the post-JavaScript DOM. →
[`workflows/golden-path-smoke-test.md`](workflows/golden-path-smoke-test.md).

### Phase 8 — End-to-End + Integration Tests
Add ≥1 **full end-to-end test** driving the whole stack as a user does (browser → API → agent → DB →
back), nothing mocked beyond the LLM stub. **Gate:** integration and E2E tests pass reliably.

### Phase 9 — Advanced Observability
The structured-logging + token/cost baseline already lands in Phase 2. This phase adds aggregation:
per-run metrics, latency, and — if specified — trace export (OpenTelemetry GenAI / an LLM tracing
backend). **Gate:** per-run token, cost, and latency are queryable in aggregate; errors carry `run_id`.

### Phase 10 — Polish + Hand-off
Fix rough edges, improve error messages, update docs. Final drift audit; accurate README.
**Gate:** drift audit passes; README reviewed by user; user accepts hand-off.

---

## Agentic layers by phase

The baseline layers (memory, MCP tools, retrieval, evals) land **stubbed in Phase 2** above. The
earns-its-place layers land later, each only when `02-architecture.md` says the agent needs it:

| Layer | Lands at | Trigger |
|-------|----------|---------|
| Real MCP servers / integrations | Phase 3 / 5 | the agent acts on a real external system |
| Long-term memory + real retrieval / RAG | Phase 3 / 5 | answers depend on cross-session memory or a corpus |
| Human-in-the-loop ([`patterns/guardrails-and-hitl.md`](patterns/guardrails-and-hitl.md)) | Phase 4 | the agent gains a real irreversible/high-stakes action |
| Durable execution / checkpointing ([`patterns/durability.md`](patterns/durability.md)) | Phase 4 / 8 | runs become long, resumable, or must survive a restart |
| Multi-agent topologies ([`patterns/multi-agent.md`](patterns/multi-agent.md)) | Phase 5+ | an escalation criterion is met |
| Advanced observability + richer evals ([`patterns/observability-and-evals.md`](patterns/observability-and-evals.md)) | Phase 9 | trace export / aggregate metrics / LLM-judge suite needed |

---

## Phase gates

A phase is complete when ALL hold: code committed and pushed · tests pass · tree clean · session report
updated · qa-auditor (or manual checklist) signed off. For Phase 1 specifically, `alembic upgrade head`
has been run against the real DB and confirmed.

**Never mark a phase complete with any gate red.** Never claim a pass on tests that use a different DB
driver than production (→ `tech-stack.md` § Database & Tests).

The current phase is recorded in the active session report and in commit messages (`phase-N: …`);
`git log --oneline | grep "phase-"` shows the history.

## Adapting the phases

The planner may merge, split, or reorder phases (a pure CLI tool skips 6–7; a no-DB project shrinks 1; a
multi-integration project splits 5). The core principle holds: **minimal working thing first.**

---

## Language-specific gate commands

The gate command depends on the language; the tech-designer sets it in `tech-stack.md`, the planner uses
it in phase definitions.

| Language | Phase 1 gate | Phase 2 gate |
|----------|-------------|-------------|
| Python | `uv run alembic upgrade head` + `uv run pytest` | `uv run pytest` (prod DB driver, automated via conftest) |
| TypeScript (Bun) | migration tool + `bun test tests/unit/` | `bun test tests/integration/` |
| TypeScript (Node) | migration tool + `npx vitest run tests/unit/` | `npx vitest run tests/integration/` |
| Go | `migrate up` + `go test ./internal/...` | `go test ./...` |

The Phase 2 gate must pass with **no LLM API key set**, regardless of language — the DB URL is set,
the LLM is stubbed. Projects with a UI add a browser E2E run (`uv run pytest tests/e2e/` or
`npx playwright test`) against the live server at Phase 7/8.
