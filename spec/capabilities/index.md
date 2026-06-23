# Capabilities Index

## Capabilities in This Project

| Capability | File | Phase |
|-----------|------|-------|
| Dataset Management | [dataset_management.md](dataset_management.md) | Phase 1 |
| NL Query | [nl_query.md](nl_query.md) | Phase 1 |
| Response Formatting | [response_formatting.md](response_formatting.md) | Phase 1 |
| Audit Log | [audit_log.md](audit_log.md) | Phase 1 |
| Session Management | [session_management.md](session_management.md) | Phase 1 |

## How to Add a New Capability

Run `/zero-shot-build [description]` on the existing spec. The spec-writer sub-agent will:
1. Create a new file in this directory (`<name>.md`, no number prefix)
2. Update this index
3. Flag any dependencies on existing capabilities
4. Self-review that it fits the architecture and data model before returning
