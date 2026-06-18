# Pattern: Observability & Evals

**Canonical home for layer 9 (Observability + evals)**
([`../agentic-architecture.md`](../agentic-architecture.md)). How you see what the agent did and prove
its answers are good. Other docs (`react-agent.md`, `phases.md`) link here for the details.

---

## Observability — three signals

1. **Structured logs** — every node emits a JSON log bound to `run_id` (and `thread_id` for multi-turn).
   No bare `print`; one structured event per node with the action's `description`.
2. **Usage** — every LLM call records input/output tokens + estimated cost, accumulated on the run.
   Sub-agent usage rolls up to the parent run ([`multi-agent.md`](multi-agent.md)). Token/cost per run
   must never be invisible.
3. **Traces** — spans following the **OpenTelemetry GenAI semantic conventions** (one span per LLM call,
   tool call, retrieval), exported to a tracing backend (LangSmith / Langfuse / OTLP — pick from
   [`../tech-stack.md`](../tech-stack.md) § Agentic Stack Tech). A trace shows the whole reason → act →
   observe path for one run.

The user-facing reasoning trace (`action_history` with plain-English `description`s) is a **product**
surface, not just an ops one — see [`react-agent.md`](react-agent.md) § State. Glass box, never a
spinner over a black box.

## Evals — plumbing tests aren't quality tests

A run can pass every layer (200, valid schema, no crash) and still return a **wrong answer**. Evals
catch that. Keep them small, fixed, and version-controlled.

- **Offline eval set** — a handful of representative `input → expected` (or rubric/property) cases.
  - Exact/structural checks where outputs are deterministic.
  - **LLM-as-judge** (rubric scoring) where outputs are open-ended — judge with a capable model
    (Opus 4.8) against an explicit rubric.
  - Component evals: retrieval recall@k ([`retrieval.md`](retrieval.md)), tool-selection accuracy.
- **Run modes** — against the **stub** for deterministic CI (catches regressions in plumbing + logic),
  and against the **real model** when validating a prompt/model change (catches answer-quality drift).
- **Regression gate** — evals run in CI; a drop below the threshold fails the build. This is what makes
  prompt/model changes safe to ship.

## What lands when

- **Phase 2 (baseline):** structured per-`run_id` logs + token/cost on the run + an **eval-harness
  skeleton** (one tiny dataset, one assertion, runs against the stub in CI). This is a gate item — see
  [`../phases.md`](../phases.md).
- **Earns its place:** OTel trace export + aggregate per-run metrics/latency dashboards, and a richer
  eval suite (LLM-judge, component evals) as the agent's answers get more open-ended.

## Don't log secrets

Usage and traces must never carry secret values — presence-only, per
[`../secret-hygiene.md`](../secret-hygiene.md).
