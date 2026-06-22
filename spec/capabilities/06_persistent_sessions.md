# Capability: Persistent Sessions

## What It Does

Creates, loads, and persists conversational sessions — including conversation history and the association between a session and its registered datasets — so that all context survives a server restart.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| session_id | UUID string | Chat API request header or body | No (new session created if absent) |
| user_message | string | Chat API request | Yes |
| assistant_response | string | Response Synthesiser output | Yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| session_id | UUID string | HTTP response body; client must include in subsequent requests |
| session_created_at | ISO-8601 datetime | SQLite `sessions` row |
| session_last_active | ISO-8601 datetime | SQLite `sessions` row (updated on every turn) |
| conversation_turn_id | UUID string | SQLite `conversation_turns` row |
| history | array of `{role, content, created_at}` | GET session history API response |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite (via SQLAlchemy) | SELECT session by `session_id`; INSERT new session; INSERT `conversation_turns` row; UPDATE `session.last_active` | Fatal: return HTTP 500; log error |

## Business Rules

- A session is created on the first chat message if no `session_id` is provided. The server generates a UUID and returns it to the client.
- The client is responsible for including `session_id` in all subsequent requests for the same conversation.
- A session is never deleted automatically. Soft-delete (via admin endpoint) is out of scope for v1.
- Sessions are not scoped to a user or browser; any client with the `session_id` can read and continue the session (single-user deployment assumption).
- Conversation turns are stored in insertion order; `turn_index` (integer, auto-increment per session) is used for ordering.
- Both the user message and the assistant response for a turn are stored in separate rows in `conversation_turns` with `role = "user"` and `role = "assistant"` respectively.
- On server startup, all active sessions are available immediately because state is in SQLite, not in-memory. No warm-up or reload step is required.
- DuckDB tables are re-registered from the SQLite `datasets` catalogue on server startup (all rows with `is_active = true`).

> **Assumed:** There is no session expiry or TTL in v1. Sessions persist indefinitely.

> **Assumed:** The dataset catalogue is global (not per-session). Any dataset uploaded in any context is available to all sessions. Per-session dataset scoping is a v2 feature.

## Success Criteria

- [ ] A chat request with no `session_id` returns a new UUID `session_id` in the response, and a corresponding row is present in the SQLite `sessions` table.
- [ ] A subsequent chat request with the returned `session_id` loads the existing session and the prior conversation turns are included in the context sent to Gemini.
- [ ] After a simulated server restart (teardown and reinitialisation of the FastAPI app and all in-memory state), a chat request with a previously created `session_id` loads the session and history correctly from SQLite.
- [ ] After server restart, DuckDB tables for all datasets with `is_active = true` are re-registered and queryable.
- [ ] The GET `/sessions/{session_id}/history` endpoint returns all turns in chronological order, matching what was inserted.
- [ ] A `session_id` that does not exist in SQLite returns HTTP 404.
