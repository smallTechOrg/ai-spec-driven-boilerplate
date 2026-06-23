# Data Model

---

## Storage Technology

Two stores, by design:

- **Metadata store — SQLAlchemy 2.0 + Alembic over `AGENT_DATABASE_URL` (SQLite local).** Holds *small, queryable metadata*: sessions, dataset descriptors (incl. the schema profile and token-economy fields), and the audit trail. Persists across restarts. The skeleton's `runs` table stays as-is.
- **Data store — DuckDB (embedded) at `AGENT_DUCKDB_PATH`.** Holds the *actual dataset rows*: one DuckDB table per uploaded dataset. This is where SQL runs. Raw rows live here and never enter the metadata DB or an LLM prompt (beyond capped samples).

> **Which store holds what:** dataset *rows* → DuckDB. Everything *about* a dataset (name, columns, types, row count, sample preview, audit) → SQLAlchemy/SQLite.

## Entities

### Entity: Session (`sessions`, SQLAlchemy)

A persistent workspace grouping a user's datasets and audit trail. Phase 1 auto-creates/uses a single default session; the model supports many.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Text (uuid) | yes | Primary key |
| name | Text | yes | Display name (default `"Default session"`) |
| created_at | TIMESTAMP(tz) | yes | Creation time |
| updated_at | TIMESTAMP(tz) | yes | Last activity |

### Entity: Dataset (`datasets`, SQLAlchemy)

A descriptor for an uploaded file ingested into DuckDB.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Text (uuid) | yes | Primary key |
| session_id | Text (FK→sessions.id) | yes | Owning session |
| name | Text | yes | User-facing name (derived from filename) |
| source_filename | Text | yes | Original filename |
| duckdb_table | Text | yes | DuckDB table name holding the rows (sanitized, unique) |
| row_count | Integer | yes | Number of rows ingested |
| schema_json | Text (JSON) | yes | Column descriptors: `[{name, type}]` |
| sample_rows_json | Text (JSON) | yes | Capped preview (≤ `AGENT_MAX_SAMPLE_ROWS`) — **token-economy field**: the only rows ever shown to the LLM |
| created_at | TIMESTAMP(tz) | yes | Ingestion time |

### Entity: AuditLog (`audit_logs`, SQLAlchemy)

One row per data operation (every ask). The auditable trail.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Text (uuid) | yes | Primary key (== run_id for an ask) |
| session_id | Text (FK→sessions.id) | yes | Owning session |
| dataset_id | Text (FK→datasets.id) | no | Target dataset (null if resolution failed) |
| nl_question | Text | yes | **Audit field** — the natural-language question |
| generated_sql | Text | no | **Audit field** — the SQL the agent generated |
| row_count | Integer | no | **Audit field** — rows the query returned |
| duration_ms | Integer | no | **Audit field** — execution time in ms |
| status | Text | yes | `completed` \| `failed` |
| error_message | Text | no | Error if failed |
| created_at | TIMESTAMP(tz) | yes | **Audit field** — timestamp of the operation |

### DuckDB layout (data store)

- One table per dataset, named `dataset_<short-id>` (recorded in `datasets.duckdb_table`). Columns and types are inferred at ingest (pandas → DuckDB).
- No cross-table foreign keys; Phase-4 cross-dataset queries join these tables by name.
- The DuckDB file at `AGENT_DUCKDB_PATH` is the single data file; deleting a dataset drops its table.

### Relationships

```
Session 1───* Dataset 1───* AuditLog
   └──────────────────────* AuditLog   (audit belongs to a session, optionally a dataset)
Dataset 1───1 DuckDB table   (datasets.duckdb_table → physical table in AGENT_DUCKDB_PATH)
```

## Data Lifecycle

- **Create:** Session on first use; Dataset + DuckDB table on upload; AuditLog on each ask.
- **Read:** Datasets listed per session; audit listed per session, newest first; DuckDB read on each ask.
- **Update:** `sessions.updated_at` on activity. Datasets/audit are immutable once written.
- **Delete:** (Phase 1) none from the UI; deleting a dataset (later) drops its DuckDB table and cascades its audit rows. Nothing is auto-expired — the audit trail is permanent by design.

## Sensitive Data

The dataset rows may contain the user's private/PII data — this is exactly why they stay local. Protections: rows live only in DuckDB on the user's machine; only schema + ≤`AGENT_MAX_SAMPLE_ROWS` sample rows + aggregates are ever sent to Gemini; no auth/secret fields are stored; the only secret is `AGENT_GEMINI_API_KEY`, read from `.env`, never logged or echoed.
