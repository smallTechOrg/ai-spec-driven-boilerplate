# Capability: Multi-Turn Conversation

## What It Does

Groups questions about a dataset into a persistent conversation so that follow-up questions ("now
filter that to 2024", "what about by region?") build on prior turns as context.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| conversation id | uuid | client (or created on first turn) | yes (after first turn) |
| new question | string (NL) | user | yes |
| prior turns | list of `message` rows | SQLite (`messages`, by conversation) | yes (assembled into context) |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| new user + assistant messages | rows in `message` | SQLite (persisted) |
| context-aware answer | answer text + result table | SSE → UI (see [`02-natural-language-query.md`](02-natural-language-query.md)) |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | load recent turns for the conversation; append new turns | DB error → `api_error("DB_ERROR", …, 500)` |
| (downstream) NL-query capability | runs the actual ReAct loop with prior turns in context | see [`02-natural-language-query.md`](02-natural-language-query.md) |

## Business Rules

- A conversation is **bound to exactly one dataset** (no switching datasets mid-conversation; no
  cross-dataset queries — [`../01-vision.md`](../01-vision.md)).
- **Short-term memory:** recent conversation turns are assembled into context (most recent N verbatim;
  older turns summarized if the budget is exceeded) per
  [`memory-and-context.md`](../../engineering/patterns/memory-and-context.md). No long-term memory
  across conversations in v1.
- Conversation history **persists** in SQLite and is retrievable for display and for context on the
  next turn.
- A follow-up must be interpretable against the prior turn — e.g. "now just 2024" should narrow the
  previous result, which means the prior turn measurably influences the newly generated query.

## Success Criteria

- [ ] Asking a question, then a follow-up that references it ("now just 2024"), produces a result that
      correctly narrows the first answer — confirming prior turns reached the agent's context.
- [ ] Conversation history is retrievable in order via the history endpoint
      ([`../05-api.md`](../05-api.md)) after the turns complete.
- [ ] A follow-up that depends on context is answered differently than if asked cold (the generated
      query reflects the prior turn) — verified by an eval case comparing the two.
- [ ] Each turn (user question + assistant answer) is persisted as `message` rows tied to the
      conversation.
