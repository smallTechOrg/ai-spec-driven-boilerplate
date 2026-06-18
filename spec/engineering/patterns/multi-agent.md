# Pattern: Multi-Agent Orchestration

**Canonical home for layer 6's multi-agent topologies**
([`../agentic-architecture.md`](../agentic-architecture.md)). The single-agent ReAct loop is the default
([`react-agent.md`](react-agent.md)); this is what to do when one loop can't keep the task coherent.

---

## Escalation criteria — earn it first

Start with one ReAct loop. **Do not** reach for multi-agent until a single loop demonstrably fails. Real
signals that justify escalation:

- The task has **distinct sub-skills** that need different tools, prompts, or models (e.g. research vs.
  writing vs. code review).
- A single context window can't hold everything and **compaction loses too much**.
- You need **parallelism** — independent subtasks that should run concurrently.
- You need an **independent check** — one agent shouldn't both produce and grade its own work.

If none of these hold, a single loop with good tools and memory is cheaper, faster, and easier to debug.
Multi-agent adds latency, cost, and coordination failure modes — it is not a default.

## Topologies

| Topology | Shape | Use when |
|----------|-------|----------|
| **Supervisor / worker** | a router agent delegates to specialized workers and integrates results | distinct sub-skills; the supervisor owns the plan |
| **Planner–executor** | one agent decomposes into a plan, another executes steps | the plan is worth fixing before acting |
| **Evaluator–optimizer** | a generator proposes, a critic scores, loop until threshold | quality matters and is checkable (drafts, code) |
| **Reflection** | the agent critiques and revises its own output before finalizing | single-agent quality boost without a second agent |

In LangGraph these are subgraphs/nodes wired into the parent `StateGraph` — not separate processes.

## State isolation

Each sub-agent gets its **own scoped state** — it should not see the parent's full `action_history` or
the other workers' scratch. Pass an explicit, minimal **task contract** in and a **typed result** out.
Shared, unscoped state across agents is the top cause of multi-agent incoherence and runaway loops.

- The supervisor holds the master plan + integrated results.
- Workers get `{task, inputs, constraints}` and return `{result, status, notes}`.
- Usage (tokens/cost) from every sub-agent **rolls up** to the parent run — see
  [`observability-and-evals.md`](observability-and-evals.md).

## Guards still apply

Every sub-agent is a ReAct loop and keeps all the mandatory mechanics from
[`react-agent.md`](react-agent.md): max-iterations → `force_finalize`, the action-safety boundary,
self-correction. A multi-agent system without per-agent iteration guards can loop unboundedly across
agents — bound the **total** work (a global step budget), not just each loop.

## Baseline vs. earns-its-place

- **Baseline:** single ReAct loop with reflection available as a same-agent quality step.
- **Earns its place:** true multi-agent topologies, only when an escalation criterion above is met and
  recorded in `02-architecture.md` § Agentic stack layers used.
