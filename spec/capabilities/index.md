# Capabilities Index

## Capabilities in This Project

| Capability | File | Phase |
|-----------|------|-------|
| CSV Analysis (upload + text answer) | [csv_analysis.md](csv_analysis.md) | Phase 1 |
| Chart Generation (code gen + sandboxed exec + PNG) | [chart_generation.md](chart_generation.md) | Phase 2 |

## What Is a Capability?

A capability is a single, discrete action or behavior the agent performs:

- **CSV Analysis** — accept a CSV upload, hold it in memory as a pandas DataFrame, answer natural-language questions by sending the schema and sample rows to Gemini and returning a plain-English text answer
- **Chart Generation** — have Gemini write pandas/matplotlib code, execute it in a sandboxed environment, and return the resulting chart as a base64 PNG alongside the executed code

## How to Add a New Capability

Run `/zero-shot-build [description]` on the existing spec. The spec-writer sub-agent will:
1. Create a new file in this directory (`<name>.md`, no number prefix)
2. Update this index
3. Flag any dependencies on existing capabilities
4. Self-review that it fits the architecture and data model before returning
