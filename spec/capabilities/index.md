# Capabilities Index

## Capabilities in This Project

| Capability | File | Phase |
|-----------|------|-------|
| File Upload | [file-upload.md](file-upload.md) | Phase 1 |
| Data Analysis | [data-analysis.md](data-analysis.md) | Phase 1 |
| Chart Rendering | [chart-rendering.md](chart-rendering.md) | Phase 1 |
| Database Connect Stub | [db-connect-stub.md](db-connect-stub.md) | Phase 1 (stub), Phase 2 (real) |

## How to Add a New Capability

Run `/zero-shot-build [description]` on the existing spec. The spec-writer sub-agent will:
1. Create a new file in this directory (`<name>.md`, no number prefix)
2. Update this index
3. Flag any dependencies on existing capabilities
4. Self-review that it fits the architecture and data model before returning
