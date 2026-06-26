# Capabilities Index

> One file per capability. Each describes exactly one discrete thing the agent can do.

---

## Capabilities in This Project

| Capability | File | Phase |
|-----------|------|-------|
| Profile uploaded CSV | [profile-csv.md](profile-csv.md) | 1 |
| Answer question with computed pandas | [answer-question.md](answer-question.md) | 1 |
| Explain the answer in plain English | [explain-answer.md](explain-answer.md) | 1 |

> Phase-2 work (resilience/retry, edge-case handling) hardens these three rather than adding new capabilities. Phase-3 adds an optional "chart the result" capability (deferred; currently a labelled UI stub).

## How to Add a New Capability

Run `/zero-shot-build [description]` on the existing spec. The spec-writer creates a `<name>.md` here, updates this index, flags dependencies, and self-reviews fit before returning.
