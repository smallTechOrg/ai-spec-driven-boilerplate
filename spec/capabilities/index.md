# Capabilities Index

> **Boilerplate status:** The spec-writer sub-agent creates one file per capability in this directory. Each file describes exactly one discrete thing the agent can do.

---

## What Is a Capability?

A capability is a single, discrete action or behavior the agent performs. Examples:
- "Search the web for companies matching criteria X"
- "Draft a personalized email given a lead profile"
- "Send a Slack notification when a threshold is crossed"

## Capabilities in This Project

| Capability | File | Status |
|-----------|------|--------|
| Ingest Dataset | [ingest-dataset.md](ingest-dataset.md) | Phase 1 (core) |
| Ask Question (NL → SQL → narrative + table) | [ask-question.md](ask-question.md) | Phase 1 (core) |
| Audit Trail | [audit-trail.md](audit-trail.md) | Phase 1 (core) |
| Visualize Result | [visualize-result.md](visualize-result.md) | Deferred — Phase 2 (stub in P1) |
| Senior-Analyst Workflow | [senior-analyst-workflow.md](senior-analyst-workflow.md) | Deferred — Phase 3 |
| Cross-Dataset Query & Dashboards | [cross-dataset-query.md](cross-dataset-query.md) | Deferred — Phase 4 (stub in P1) |

## How to Add a New Capability

Run `/zero-shot-build [description]` on the existing spec. The spec-writer sub-agent will:
1. Create a new file in this directory (`<name>.md`, no number prefix)
2. Update this index
3. Flag any dependencies on existing capabilities
4. Self-review that it fits the architecture and data model before returning

## Capability File Template

Each capability file should answer:
- **What it does** (one sentence)
- **Inputs** (what data it receives)
- **Outputs** (what it produces)
- **External calls** (APIs, LLMs, databases it touches)
- **Error cases** (what can go wrong and how it's handled)
- **Success criteria** (how we test it)
