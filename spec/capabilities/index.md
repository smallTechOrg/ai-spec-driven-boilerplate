# Capabilities Index

One file per capability. Each describes exactly one discrete thing the agent can do. **Active (Phase 1): 3 capabilities.** The rest are deferred to later phases.

---

## What Is a Capability?

A capability is a single, discrete action or behavior the agent performs.

## Capabilities in This Project

| Capability | Phase | Status | File |
|-----------|-------|--------|------|
| Ingest & profile a dataset | 1 | ACTIVE | [ingest-and-profile.md](ingest-and-profile.md) |
| Answer a question (plan-then-execute, privacy boundary) | 1 | ACTIVE | [answer-question.md](answer-question.md) |
| Audit & cost tracking | 1 | ACTIVE | [audit-and-cost.md](audit-and-cost.md) |
| Dataset library & cross-day restore | 2 | DEFERRED | [library-and-restore.md](library-and-restore.md) |
| Multi-file join & folder-as-dataset | 3 | DEFERRED | [multi-file.md](multi-file.md) |
| Proactivity, clarification & watched folder | 4 | DEFERRED | [proactivity-and-clarify.md](proactivity-and-clarify.md) |
| Cost rollup, derived tables & reproducible re-run | 5 | DEFERRED | [durability.md](durability.md) |

The three ACTIVE Phase-1 capabilities together form the one core loop: load a file, ask a question, get a trustworthy answer that is recorded. Everything else is a labelled stub until its phase.

## How to Add a New Capability

Run `/zero-shot-build [description]` on the existing spec. The spec-writer sub-agent will create the file, update this index, flag dependencies, and self-review before returning.

## Capability File Template

Each capability file answers: What it does · Inputs · Outputs · External calls · Business rules · Success criteria.
