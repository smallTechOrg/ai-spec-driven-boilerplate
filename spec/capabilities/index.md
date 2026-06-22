# Capabilities Index

## Capabilities in This Project

| # | Capability | File |
|---|-----------|------|
| 1 | Dataset Store and Organise | [01_dataset_store.md](01_dataset_store.md) |
| 2 | Natural Language to SQL | [02_nl_to_sql.md](02_nl_to_sql.md) |
| 3 | Rich Responses | [03_rich_responses.md](03_rich_responses.md) |
| 4 | Senior Analyst Workflow | [04_senior_analyst.md](04_senior_analyst.md) |
| 5 | Token Economy | [05_token_economy.md](05_token_economy.md) |
| 6 | Persistent Sessions | [06_persistent_sessions.md](06_persistent_sessions.md) |
| 7 | Audit Log | [07_audit_log.md](07_audit_log.md) |

## Capability Dependency Map

```
User Upload
  └── 01_dataset_store       ← file ingest, DuckDB registration, SQLite catalogue

User Question
  └── 06_persistent_sessions ← load/create session, load history
       └── 05_token_economy  ← select schemas, window history
            └── 02_nl_to_sql ← Gemini tool-use, SQL execution, destructive-SQL guard
                 ├── 04_senior_analyst  ← clarification, decomposition, quality notes, suggestions
                 ├── 03_rich_responses  ← format markdown table + narrative
                 └── 07_audit_log       ← append-only entry
```

## How to Add a New Capability

Run `/zero-shot-build [description]` on the existing spec. The spec-writer sub-agent will:
1. Create a new file in this directory (`<name>.md`, no number prefix)
2. Update this index
3. Flag any dependencies on existing capabilities
4. Self-review that it fits the architecture and data model before returning
