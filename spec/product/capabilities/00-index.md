# Capabilities Index

> **Boilerplate status:** The spec-writer sub-agent creates one file per capability in this directory. Each file describes exactly one discrete thing the agent can do.

---

## What Is a Capability?

A capability is a single, discrete action or behavior the agent performs. Examples:
- "Search the web for companies matching criteria X"
- "Draft a personalized email given a lead profile"
- "Send a Slack notification when a threshold is crossed"

## Capabilities in This Project

| # | Capability | File |
|---|-----------|------|
| 1 | Discover SMB candidates | [01-discover-candidates.md](01-discover-candidates.md) |
| 2 | Extract firmographics | [02-extract-firmographics.md](02-extract-firmographics.md) |
| 3 | Score data-maturity gap | [03-score-data-gap.md](03-score-data-gap.md) |
| 4 | Export leads as CSV | [04-export-csv.md](04-export-csv.md) |

## How to Add a New Capability

Run `/spec-new-capability [description]` or ask the spec-writer directly. The spec-writer will:
1. Create a new file in this directory
2. Update this index
3. Flag any dependencies on existing capabilities
4. The spec-reviewer will validate it fits the architecture

## Capability File Template

Each capability file should answer:
- **What it does** (one sentence)
- **Inputs** (what data it receives)
- **Outputs** (what it produces)
- **External calls** (APIs, LLMs, databases it touches)
- **Error cases** (what can go wrong and how it's handled)
- **Success criteria** (how we test it)
