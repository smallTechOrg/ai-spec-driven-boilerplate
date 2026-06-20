# Agent

> Filled by the **spec-writer** from intake. Part 3 of the 4-part spec contract (see `harness/harness.md`).
> The layer **on/off ledger** for this build: which of the 11 agentic layers are ON. Baseline layers ship in
> Phase 1 and are pre-checked — leave them on unless you have a reason. The earns-its-place layers stay OFF
> until a capability needs them; turning one on is a deliberate cost. Each pattern recipe lives at the path
> shown; don't restate it here — name the layer, mark it ON/OFF, give the one-line *why for this agent*.
>
> **Every baseline layer here is delivered by the reused, version-pinned TESTED CORE** (code is truth there,
> like a framework dependency — see `spec/constitution.md` § two-zone model). `/build` does not regenerate
> the loop, server, config, persistence, or `/traces` dashboard; it fills the GENERATED DOMAIN seams
> (capability nodes, tools, prompts, EARS evals, domain screens) on top of that proven core. The
> non-negotiable correctness rules each layer must satisfy are enumerated in `spec/constitution.md` — this
> ledger only decides which layers are wired on.

## Layers

Mark `[x]` ON / `[ ]` OFF. The "why" is one line, specific to **this** agent (not the generic layer).

### Baseline — ON in Phase 1 (the raised default; leave on unless you have a reason)

- [x] **L1 · Model & providers** — `harness/patterns/model-and-providers.md`
  Runtime LLM behind `init_chat_model`; provider/model pinned in `spec/tech-stack.md` (cheap tier default).
  This agent: plain tool-calling on `claude-haiku-4-5` — no long context, JSON mode, or vision needed; a
  ticket is short text and the loop reads tool output to compose the reply.
- [x] **L2 · Context engineering** — `harness/patterns/context-engineering.md`
  Assemble the window each turn: domain system prompt + goal + tool results, within a token budget.
  This agent: the triage domain prompt (urgency/category enums + grounding rules) + the ticket text +
  classify/policy tool output stay in context; nothing else needed.
- [x] **L3 · Memory (working / short-term only)** — `harness/patterns/memory.md`
  In-run scratchpad + message history. **Long-term / cross-run memory is OFF** (see earns-its-place below).
  This agent: within a run it must remember the ticket text and the classify result while drafting the reply;
  a checkpointer gives a follow-up turn ("make it more apologetic") the prior draft (generate-then-refine —
  carried by the transcript, NOT sessions.py: the ticket arrives in the goal, not as a reused upload).
- [x] **L4 · Tools & MCP** — `harness/patterns/tools-and-mcp.md`
  Internal actions = plain typed `@tool` in-process; **MCP only for external integrations** (OAuth2.1, no static secrets).
  This agent: `classify_ticket` (P1), `search_policy` (P1, knowledge corpus), `escalate_ticket` (P2 stub),
  `summarize_thread` (P3 stub), plus `write_todos` + `finish`. All in-process; no MCP, no external API key.
- [x] **Orchestration · ReAct Deep-Agent loop** — `harness/patterns/react-agent.md`
  LangGraph `StateGraph`: `agent → (tools → agent)* → finalize`, with planning todos + a `finish` tool.
  Core invariants (from `spec/constitution.md`): `max_iterations` sized to worst-case tool depth (not the
  happy path), a `force_finalize` fallback chain that never returns a blank answer, and graceful degradation
  on non-critical external failures. Code-executing tools use AST-validated eval, never regex dispatch.
  This agent: worst-case tool depth is write_todos -> classify_ticket -> search_policy -> finish, so
  `max_iterations` = 6 (default) is comfortably sized; no sub-agent split; no code-executing tool.
- [x] **L7 · Guardrails (action-safety only)** — `harness/patterns/guardrails-and-hitl.md`
  Validate tool inputs, refuse out-of-scope/unsafe actions per the domain rules. **HITL pause is OFF** (below).
  This agent: action-safety is prompt-level — it DRAFTS replies but never performs an irreversible action
  (issue a refund, delete an account, charge a card); there is no mutating/code-exec tool, so no AST-eval
  `guardrails.py` is generated (`C-ACTION-SAFETY` triggers only on a code/SQL-executing tool). The refusal
  is verified by the P1 EARS line `test_refuses_irreversible_action`.
- [x] **L9 · Observability & Evals** — `harness/patterns/observability-and-evals.md`
  OTel-GenAI spans → SQLite → built-in, self-contained **organized `/traces` observability dashboard**
  (overview + drill-down; no Docker/signup) for a non-technical operator. Outcome eval is the **hard gate**
  for the v1 single-capability slice (a 200 with the wrong answer FAILS, multi-sampled with margin so
  exit 0 is deterministic); trajectory eval is advisory until a 2nd capability exists. Each EARS line is
  bound to an executable check via its `[@eval]` token — that binding is what "proves it ran."
  This agent: the hard outcome eval judges the P1 triage answer against
  `tests/test_triage_ticket_gate.py::test_triage_classifies_and_drafts` — it must carry an urgency label, a
  category label, and a drafted reply with a next step. Trajectory (classify_ticket fired) is advisory until
  capability #2.
- [x] **L10 · Interface / serving** — `harness/patterns/interface.md`
  Async FastAPI: `GET /health`, `POST /runs`, `GET /traces`. Port **8001**. One JSON envelope everywhere:
  routes return `ok(data)` or raise `api_error(...)` — a failed run reads `state['error']`, logs with
  `run_id`, and returns `api_error('RUN_FAILED', status=500)` (no `error.html`). Serves the static
  Next.js export from the same port/command.
  This agent: the standard `/health`, `POST /runs`, `/traces`; a single-page UI (paste ticket -> triaged
  result + drafted reply -> trace link). No SSE in v1; the answer returns whole.
- [x] **L11 · Deploy & Operate** — `harness/patterns/deploy.md`
  Portable artifact (`langgraph.json` / Dockerfile); local SQLite → Postgres + Redis on the prod ladder.
  This agent: deploy target deferred to `/deploy` (TBD); no deploy work in Phase 1.

> Persistence (the data spine — `harness/patterns/persistence.md`) is not a toggle: it's always on.
> Async SQLAlchemy 2.0, SQLite (`aiosqlite`) local → Postgres (`asyncpg`) prod. Tables: `runs`, `messages`,
> `spans` (+ domain entities); `runs` carries `input_tokens`/`output_tokens`/`cost_usd`/`thread_id` from
> Phase 1. Never `psycopg2`. **Session-scoped resources** (e.g. a parsed file/DataFrame/index keyed by
> `session_id`) persist across follow-up turns and are released only on explicit session delete —
> per-question release is a `SESSION_DATA_LOST` correctness bug on Q2.

### Earns its place — OFF by default (turn ON only when a capability needs it; that's the deliberate cost)

- [ ] **L5 · Retrieval / RAG** — `harness/patterns/retrieval.md`
  ON only if the agent must ground answers in a corpus it doesn't already know.
  OFF — the support-policy grounding is a tiny in-process keyword lookup (`search_policy` @tool over a
  bundled dict, the `search_docs` shape in `tools-and-mcp.md`), not a vector/RAG index. No embedding store
  earns its place for a handful of policy passages; promote to L5 only if the corpus grows.
- [ ] **L3+ · Long-term / cross-run memory** — `harness/patterns/memory.md`
  ON only if the agent must remember facts *across* separate runs/users.
  OFF — each ticket is triaged independently; nothing carries across separate runs.
- [ ] **L6 · Multi-agent (supervisor + sub-agents)** — `harness/patterns/multi-agent.md`
  ON only if one ReAct loop genuinely can't hold the task; sub-agents get isolated context.
  OFF — triage is a single short reasoning loop; no split needed.
- [ ] **L7+ · HITL (human-in-the-loop pause)** — `harness/patterns/guardrails-and-hitl.md`
  ON only if a dangerous/irreversible action must pause for human approval mid-run.
  OFF — the agent only drafts; it performs no irreversible action, so there is nothing to pause on.
- [ ] **L8 · Durability (checkpointer / resume)** — `harness/patterns/durability.md`
  ON only if a run is long/expensive enough that surviving a crash or restart matters.
  OFF — a triage run is a few cheap-tier calls; on a crash the rep simply re-submits the ticket.
  (The AsyncSqliteSaver checkpointer is on for short-term multi-turn memory, not crash-durability.)

## Notes
> "Done" for this agent = the mechanical gate exits 0: the full deterministic test pyramid (FakeModel inner
> loop) + a robust live two-turn E2E over HTTP against the real model + the outcome eval passing. The gate is
> the only blocking verdict; spec/plan/qa + UI screenshot reviews run every build and their fixes are applied,
> but the build stays unattended after the single Q4 approval. Non-negotiables live in `spec/constitution.md`.

Layer interaction note: `search_policy` (grounding) and `classify_ticket` (routing) are both base-loop
in-process tools; the loop calls classify first (routing) then policy (grounding) then drafts and finishes.
The checkpointer (short-term memory) lets a follow-up "make the reply more apologetic" reuse the prior
draft from the transcript without re-pasting the ticket — generate-then-refine, so no sessions.py.
