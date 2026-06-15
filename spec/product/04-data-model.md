# Data Model

## Storage Technology

SQLite via SQLAlchemy 2.0 (sync). Single file database, no server process required. Alembic manages schema migrations.

## Entities

### Entity: Dataset

Represents a single uploaded CSV file.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | TEXT (UUID) | yes | Primary key |
| filename | TEXT | yes | Original filename from upload |
| file_path | TEXT | yes | Path on disk where CSV is stored |
| row_count | INTEGER | no | Number of rows in the CSV (set after parse) |
| column_names | TEXT | no | JSON-encoded list of column names |
| created_at | TIMESTAMP | yes | When the dataset was uploaded |

### Entity: QueryRecord

Represents one natural language query made against a Dataset.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | TEXT (UUID) | yes | Primary key |
| dataset_id | TEXT (FK) | yes | References Dataset.id |
| question | TEXT | yes | The user's natural language question |
| answer | TEXT | no | The LLM's plain-text answer (null while processing) |
| status | TEXT | yes | pending / completed / failed |
| error_message | TEXT | no | Error detail if status=failed |
| created_at | TIMESTAMP | yes | When the query was submitted |
| updated_at | TIMESTAMP | yes | When the record was last modified |

### Entity: AgentRun

Internal record tracking each LangGraph pipeline invocation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | TEXT (UUID) | yes | Primary key |
| query_record_id | TEXT (FK) | yes | References QueryRecord.id |
| status | TEXT | yes | pending / completed / failed |
| error_message | TEXT | no | Error detail if failed |
| created_at | TIMESTAMP | yes | Run start time |
| updated_at | TIMESTAMP | yes | Last update |

### Relationships

```
Dataset (1) ──< QueryRecord (N)
QueryRecord (1) ──< AgentRun (N)
```

## Data Lifecycle

- **Dataset**: created on upload; never deleted in v0.1.
- **QueryRecord**: created when user submits a question; answer written after pipeline completes.
- **AgentRun**: created at pipeline start; updated to `completed` or `failed` at end.

## Sensitive Data

- CSV files may contain PII depending on what the user uploads. No special handling in v0.1 — files stored as-is on local disk. Multi-user deployments must add access controls before exposing this app.
- No API keys stored in the database.
