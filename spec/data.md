# Data Model

Two stores (see [architecture.md](architecture.md#duckdb-vs-metadata-db-split)):
- **Metadata DB** (SQLAlchemy, `AGENT_DATABASE_URL`): the entities below.
- **DuckDB** (`data/analytics.duckdb`): one columnar table per dataset, `ds_<dataset_id>`, holding the actual rows.

## Entities (metadata DB)

### Dataset
| Field | Type | Notes |
|-------|------|-------|
| id | str (uuid) | PK |
| name | str | original filename / display name |
| duckdb_table | str | DuckDB table name (`ds_<id>`) |
| schema_json | JSON/Text | `[{name, type}]` column schema (source of LLM context) |
| row_count | int | rows ingested |
| created_at | timestamp | |

### Session
| Field | Type | Notes |
|-------|------|-------|
| id | str (uuid) | PK |
| title | str | default "New session" |
| created_at | timestamp | |
| updated_at | timestamp | |

> **Assumed:** a Session is not bound to a single dataset — each query names its `dataset_id`. This keeps Phase 3 multi-dataset natural.

### Message
| Field | Type | Notes |
|-------|------|-------|
| id | str (uuid) | PK |
| session_id | str | FK → Session |
| role | str | `user` \| `assistant` |
| content | Text | user question, or assistant answer |
| sql | Text \| null | the executed SQL (assistant only) |
| result_json | JSON/Text \| null | `{columns, rows}` for the result table (assistant only) |
| dataset_id | str \| null | dataset queried |
| created_at | timestamp | |

### AuditLog
| Field | Type | Notes |
|-------|------|-------|
| id | str (uuid) | PK |
| session_id | str \| null | FK → Session |
| dataset_id | str \| null | FK → Dataset |
| operation | str | `query`, `ingest` |
| sql_text | Text \| null | executed SQL |
| status | str | `success` \| `error` |
| row_count | int \| null | rows returned |
| error_message | Text \| null | |
| duration_ms | int \| null | execution time |
| created_at | timestamp | |

### Run (existing `RunRow`, retained)
Tracks one graph invocation (status/error). Reused by the runner; not user-facing.

## Relationships

- Session 1—N Message
- Session 1—N AuditLog
- Dataset 1—N Message (via `dataset_id`)
- Dataset 1—N AuditLog
- Dataset 1—1 DuckDB table `ds_<id>`

## Lifecycle

1. **Ingest:** upload → DuckDB table created + `Dataset` row + `AuditLog(operation=ingest)`.
2. **Query:** user `Message` → graph → `execute_sql` writes `AuditLog(operation=query)` → assistant `Message` with `sql` + `result_json`.
3. **Persistence:** sessions/messages survive reloads (read from metadata DB).
4. **No deletion** of datasets/sessions in v1 (out of scope).
