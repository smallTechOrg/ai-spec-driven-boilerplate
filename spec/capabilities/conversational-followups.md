# Capability: Conversational Follow-ups (turn memory)

## What It Does
Lets the user ask follow-up questions that depend on prior turns ("now just for last year", "and by month?"), resolving them against conversation history so each answer is in context — without ever putting raw rows in that context.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| dataset_id / connection_id | string | active session | yes |
| question | string | chat box | yes |
| messages | list | prior turns (app store) | auto |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| answer_text + chart_spec | string + object | answer panel + chart |
| updated conversation | rows | app store (SQLite) |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini 2.5 Flash | plan with prior-turn context (schema + question history only) | `LLM_UNAVAILABLE` |
| DuckDB (local) | full-data aggregation | `COMPUTE_FAILED` |

## Business Rules
- Conversation context is prior questions/answers + schema only — never raw rows.
- A bounded recent-turn window is kept to stay frugal on tokens.
- Memory is per-dataset/connection conversation, persisted locally.

## Success Criteria
- [ ] Ask "total revenue by region", then "now just for last year" → the follow-up uses prior context correctly.
- [ ] Conversation turns persist across the session in the app store.
- [ ] No raw rows appear in any prompt across the conversation.
