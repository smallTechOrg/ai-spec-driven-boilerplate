# Data Model

## Storage Technology

Two storage systems are used:

- **SQLite** (via SQLAlchemy): persistent store for the dataset catalogue, sessions, conversation history, and audit log. File: `data/analyst.db`. Created on startup if absent.
- **DuckDB** (in-process, no separate server): query engine over uploaded files. Tables are registered as views at startup from the SQLite `datasets` catalogue. DuckDB state is in-memory per server process; it is rebuilt from SQLite on every restart.
- **Local filesystem** (`data/uploads/`): raw uploaded files (CSV, Excel). Filenames follow the pattern `<dataset_id>.<original_extension>`.

---

## Entities

### Entity: Dataset

Represents one uploaded file registered as a queryable DuckDB table.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID (TEXT) | Yes | Primary key, generated server-side at upload |
| name | TEXT | Yes | User-supplied display name (1–100 chars) |
| description | TEXT | No | User-supplied description (0–500 chars) |
| table_name | TEXT UNIQUE | Yes | Slugified DuckDB table name derived from `name`; unique among active datasets |
| file_path | TEXT | Yes | Absolute path on disk: `data/uploads/<id>.<ext>` |
| original_filename | TEXT | Yes | Filename as submitted by the browser |
| file_extension | TEXT | Yes | Lowercase extension: `csv`, `xlsx`, `xls` |
| schema_json | TEXT (JSON) | Yes | JSON array: `[{"column": "...", "dtype": "..."}]` |
| row_count | INTEGER | Yes | Exact row count at upload time |
| upload_timestamp | DATETIME | Yes | UTC timestamp of upload (ISO-8601) |
| is_active | BOOLEAN | Yes | `true` by default; set to `false` on soft-delete |

**Indexes:** `table_name` (unique, partial on `is_active = true`); `upload_timestamp`.

---

### Entity: Session

Represents one conversational context. A session groups a sequence of conversation turns.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID (TEXT) | Yes | Primary key; returned to client on first message |
| created_at | DATETIME | Yes | UTC timestamp of session creation |
| last_active | DATETIME | Yes | UTC timestamp of most recent turn; updated on every turn |

**Indexes:** `last_active`.

---

### Entity: ConversationTurn

Represents one message in a session. Both user messages and assistant responses are stored as individual rows.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID (TEXT) | Yes | Primary key |
| session_id | UUID (TEXT) | Yes | FK → `sessions.id` |
| turn_index | INTEGER | Yes | Monotonically increasing integer per session (for ordering) |
| role | TEXT | Yes | One of: `"user"`, `"assistant"`, `"system"` |
| content | TEXT | Yes | The message content (markdown for assistant turns) |
| created_at | DATETIME | Yes | UTC timestamp |
| is_summarised | BOOLEAN | Yes | `false` by default; `true` when this turn has been folded into a summary turn |

**Indexes:** `(session_id, turn_index)`; `(session_id, is_summarised)`.

**Notes:**
- A summary turn has `role = "system"` and `is_summarised = true`. It replaces all turns before it in the history window.
- Turns with `is_summarised = true` are excluded from the prompt history sent to Gemini.

---

### Entity: AuditLog

Append-only record of every SQL operation performed by the agent.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID (TEXT) | Yes | Primary key |
| session_id | UUID (TEXT) | Yes | FK → `sessions.id` |
| logged_at | DATETIME | Yes | UTC timestamp of log write |
| user_question | TEXT | Yes | The verbatim user message that triggered the SQL |
| generated_sql | TEXT | No | The last SQL statement executed in this turn; null if none |
| datasets_touched | TEXT (JSON) | Yes | JSON array of `table_name` strings referenced in the turn's SQL |
| row_count_returned | INTEGER | Yes | Number of rows in the result set (0 for errors or empty results) |
| latency_ms | INTEGER | Yes | Wall-clock milliseconds from request receipt to response assembled |
| sql_error | TEXT | No | DuckDB error message if execution failed; null otherwise |

**Indexes:** `session_id`; `logged_at`.

**Constraint:** No UPDATE or DELETE is ever issued on this table by the application. Enforced by code convention (no SQLAlchemy `update`/`delete` calls targeting `audit_log`) and verified by code review.

---

## Relationships

```
sessions (1) ──────────── (N) conversation_turns
sessions (1) ──────────── (N) audit_log
datasets   — global scope, not linked to sessions in v1
```

DuckDB tables correspond 1:1 with active `datasets` rows (by `table_name`). The DuckDB registry is rebuilt from SQLite at startup; it is not an entity in SQLite.

---

## Data Lifecycle

| Entity | Created | Updated | Deleted |
|--------|---------|---------|---------|
| Dataset | On file upload | Never (immutable after creation) | Soft-delete via `is_active = false`; file on disk never deleted |
| Session | On first chat message with no session_id | `last_active` updated on every turn | Never |
| ConversationTurn | On each user message (user role) and after each agent response (assistant role); on summarisation (system role) | `is_summarised` flipped to true when folded into summary | Never |
| AuditLog | After each SQL-executing turn | Never | Never |

---

## Sensitive Data

| Field | Risk | Protection |
|-------|------|------------|
| `GEMINI_API_KEY` | LLM API credential | Loaded only from `.env`; never stored in SQLite, never returned by any API endpoint, never logged |
| `content` (ConversationTurn) | May contain user data values quoted in questions | Stored in SQLite on local disk; no network transmission beyond the local server |
| `user_question` (AuditLog) | Same as above | Same protection |
| `file_path` (Dataset) | Internal server path | Not returned in public API responses (only `dataset_id` and `name` are); used internally only |

No PII fields are explicitly modelled for v1 (single-user, local deployment). If the deployment context changes, a PII audit is required before v3.
