# Agentic Architecture — The Stack

This is the reference architecture every agent built from this boilerplate targets. It defines the
**agentic AI stack** as ten layers, names the canonical pattern doc and default technology for each, and
states what ships in the default baseline vs. what's added when it earns its place.

The orchestration framework is **LangGraph** (the `graph/StateGraph` layout in `project-layout.md`) and
the tool/integration standard is **MCP** (Model Context Protocol). The Claude Agent SDK is a viable
alternative for Claude-native, lighter agents — note it in `02-architecture.md` if chosen, but the
default layout and patterns below assume LangGraph + MCP.

---

## The stack (bottom-up)

| # | Layer | Canonical home | Default technology |
|---|-------|----------------|--------------------|
| 1 | **Model** | [`patterns/llm-providers.md`](patterns/llm-providers.md) | Claude (Sonnet 4.6 default; route to Haiku 4.5 / Opus 4.8); structured outputs, prompt caching, extended thinking |
| 2 | **Context** | [`patterns/memory-and-context.md`](patterns/memory-and-context.md) | system-prompt assembly, window management, compaction/summarization |
| 3 | **Memory** | [`patterns/memory-and-context.md`](patterns/memory-and-context.md) | working (graph state) · short-term (session) · long-term episodic+semantic (vector store) |
| 4 | **Tools / integration** | [`patterns/tools-and-mcp.md`](patterns/tools-and-mcp.md) | typed tool registry + **MCP servers** + action-safety sandbox |
| 5 | **Retrieval / knowledge** | [`patterns/retrieval.md`](patterns/retrieval.md) | embeddings + vector DB + chunking + hybrid search + rerank (RAG) |
| 6 | **Orchestration** | [`patterns/react-agent.md`](patterns/react-agent.md) (single) · [`patterns/multi-agent.md`](patterns/multi-agent.md) (topologies) | ReAct loop default; supervisor / planner-executor / evaluator-optimizer / reflection when it earns it |
| 7 | **Guardrails + HITL** | [`patterns/guardrails-and-hitl.md`](patterns/guardrails-and-hitl.md) | input/output validation, action approval, interrupt → resume |
| 8 | **Durability / runtime** | [`patterns/durability.md`](patterns/durability.md) | LangGraph checkpointer, resumable runs, concurrency, idempotency |
| 9 | **Observability + evals** | [`patterns/observability-and-evals.md`](patterns/observability-and-evals.md) | OTel GenAI traces, token/cost/latency, tracing backend, offline + online eval harness, regression gates |
| 10 | **Interface / serving** | [`../product/05-api.md`](../product/05-api.md) · [`../product/06-ui.md`](../product/06-ui.md) · [`project-layout.md`](project-layout.md) | FastAPI + SSE streaming; webhook / schedule / CLI / UI triggers |

Exact library versions and providers for each layer are in [`tech-stack.md`](tech-stack.md) §
Agentic Stack Tech — that table is the single source of truth; this one names the *concepts*.

---

## Reference architecture

```
trigger (API / webhook / schedule / CLI)
  → API (FastAPI, SSE stream)
  → guardrails: input validation / auth                        (layer 7)
  → orchestrator: LangGraph StateGraph, checkpointed           (layers 6, 8)
       ├─ context assembly  ← memory (working/short/long)      (layers 2, 3)
       │                    ← retrieval (vector DB)             (layer 5)
       ├─ plan_action (LLM, model-routed)                      (layers 1, 6)
       ├─ act: tools / MCP  ← action-safety sandbox            (layer 4)
       ├─ observe → loop   (ReAct; escalate to sub-agents)     (layer 6)
       ├─ guardrails: output validation / HITL approval        (layer 7)
       │              (interrupt → resume)                     (layer 8)
       └─ finalize / force_finalize
  → persistence (runs, messages, memory, checkpoints)          (layers 3, 8)
  → observability (traces, token/cost, evals)                  (layer 9)
```

This is the same ReAct skeleton from [`patterns/react-agent.md`](patterns/react-agent.md), with the
memory, retrieval, tool, guardrail, durability, and observability layers wired around it.

---

## The default baseline (what every agent ships)

Per the "raise the baseline" decision, the standard build is **not** a bare loop. The first runnable
skeleton (Phase 2) includes these layers, **stubbed and offline**:

- **Model** with `provider=auto` (real when key set, stub otherwise).
- **Working + short-term memory** — graph state + session-scoped store.
- **Tools via MCP** — at least one MCP tool, behind the action-safety boundary (stubbed).
- **Retrieval** — embeddings + vector store wired, stubbed (deterministic fake vectors).
- **Eval harness skeleton** — a tiny fixed dataset + one assertion, runnable in CI against the stub.
- **Observability baseline** — structured per-`run_id` logs + token/cost on the run.

See [`phases.md`](phases.md) for exactly which layer lands in which phase and its gate.

## Earns-its-place (added when the spec calls for it)

These are real layers, not gold-plating — but they're added in a later phase, only when the agent's job
needs them. The spec (`02-architecture.md` § Agentic stack layers used) records which apply and why:

- **Long-term memory** (episodic/semantic) — when the agent must remember across sessions.
- **Real retrieval / RAG** — when answers depend on a knowledge corpus.
- **Multi-agent topologies** — when a single ReAct loop can't keep the task coherent
  ([`patterns/multi-agent.md`](patterns/multi-agent.md) § Escalation criteria).
- **Human-in-the-loop** — when an action is irreversible or high-stakes.
- **Durable execution / checkpointing** — when runs are long, resumable, or must survive a restart.
- **Advanced observability** — trace export + aggregate metrics beyond the Phase 2 baseline.

---

## How to use this file

1. `02-architecture.md` declares **which layers** this agent uses (all baseline layers + any
   earns-its-place ones) and why.
2. `tech-stack.md` § Agentic Stack Tech pins the **exact technology** per layer.
3. `07-agent-graph.md` specs the **graph** that wires the chosen layers together.
4. Each layer's behaviour is defined once in its pattern doc — never restate it elsewhere; link.
