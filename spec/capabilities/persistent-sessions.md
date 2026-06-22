# Capability: Persistent Sessions

## What It Does
Stores chat sessions and their messages so a conversation survives page reloads.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| session create/select | str (id) | sidebar | yes |
| message | {role, content, sql, result, dataset_id} | query pipeline | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| session record | Session row | metadata DB + sidebar |
| message history | list of Message rows | metadata DB + chat panel |

## External Calls
| System | Operation | On Failure |
|--------|-----------|-----------|
| Metadata DB | insert/select Session + Message | API error surfaced; UI shows retry |

## Business Rules
- Each user question and each assistant answer is persisted as a Message.
- Assistant messages persist the answer, sql, and result table (result_json).
- Reloading the page and reopening a session restores the full history.

## Success Criteria
- [ ] Creating a session and asking a question persists both messages.
- [ ] Reloading the page and selecting the session restores the answer, table, and SQL.
- [ ] Sessions are listed most-recent-first in the sidebar.
