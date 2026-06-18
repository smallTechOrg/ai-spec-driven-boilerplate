# Pattern: Memory & Context

**Canonical home for layers 2 (Context) and 3 (Memory) of the stack**
([`../agentic-architecture.md`](../agentic-architecture.md)). What the agent knows, where it's kept, and
how it's assembled into each LLM call.

---

## Three memory tiers

| Tier | Lifetime | Where it lives | Example |
|------|----------|----------------|---------|
| **Working** | one run | LangGraph state (`AgentState`) | `action_history`, current plan, scratch values |
| **Short-term** | one session (many runs) | session-scoped module store keyed by `session_id` + a `messages` table | conversation turns, the uploaded file's parsed DataFrame |
| **Long-term** | across sessions | `memory_records` table + a vector store | learned user preferences, prior findings, durable facts |

- **Working** memory is the loop's state — see [`react-agent.md`](react-agent.md) § State. Released at
  the end of the run.
- **Short-term** follows the run-vs-session lifecycle in [`react-agent.md`](react-agent.md) § Resource
  lifecycle — keyed by `session_id`, **not** `run_id`, and released only when the session is deleted.
- **Long-term** is written deliberately (not every turn) and read by semantic search at context-assembly
  time. Vector-store mechanics live in [`retrieval.md`](retrieval.md).

## Long-term write policy

Don't persist everything — that poisons recall. Write a `memory_record` only when a turn produces a
**durable, reusable fact** (a stated preference, a confirmed result, an entity the agent will need
again). Each record carries: `content`, `kind` (`episodic` | `semantic`), `salience`, `created_at`,
`session_id`, and an embedding. Evict by recency × salience (or a TTL) so the store stays small and
relevant.

## Context assembly (layer 2)

Every `plan_action` call is built from a fixed budget, highest-value first:

```
system prompt (role, rules, output contract, the FINAL ANSWER signal)
+ tool descriptions (only the tools in scope this turn)
+ retrieved context (top-k from retrieval.md, reranked)
+ long-term memory hits (top-k relevant memory_records)
+ short-term: recent messages (most recent N, older ones summarized)
+ working state: action_history (descriptions + results)
+ the user's current input
```

Assemble it in one place (a `context.build(...)` function), never ad-hoc per node, so the budget and
ordering are enforced consistently.

## Window management & compaction

The context window is finite and attention degrades as it fills ("context rot"). When the assembled
context approaches the model's budget:

- **Summarize** the oldest short-term messages into a running summary; keep the last N turns verbatim.
- **Compact** `action_history`: keep `description` + `result` for recent steps, drop raw intermediate
  payloads for old ones (their findings already live in the summary or long-term memory).
- **Never** silently truncate mid-structure — summarize, don't chop.

Prompt caching (see [`llm-providers.md`](llm-providers.md) § Model layer) makes the stable prefix
(system prompt + tool descriptions) cheap to resend every turn — keep that prefix byte-stable so it
stays cached.

## Baseline vs. earns-its-place

- **Baseline (Phase 2):** working + short-term memory, and the context-assembly function. Stubbed
  embeddings for long-term so the wiring exists offline.
- **Earns its place:** real long-term memory (when the agent must remember across sessions) and
  summarization-based compaction (when sessions get long). See [`../phases.md`](../phases.md).
