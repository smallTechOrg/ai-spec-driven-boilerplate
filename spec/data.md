# Data Model

> Two distinct stores: the **app metadata store** (SQLite) holds dataset/question/conversation metadata; the **working store** (DuckDB, local) holds the analysed rows. The analysed rows never leave the machine and never reach the LLM — only schema + aggregates do.

---

## Storage Technology

- **App metadata store:** SQLite via SQLAlchemy 2.0, migrated with Alembic. Deliberate choice for a personal local tool — it is the app's own store, NOT the analysed data. Default `sqlite:///./data/agent.db`.
- **Working store (analysed data):** DuckDB local file/in-memory. Holds uploaded CSV rows (Phase 1) and scans the connected PostgreSQL (Phase 2). Rows stay here; only aggregates computed from it cross the privacy boundary.
- **Uploaded files:** stored under a local `upload_dir` (setting), then loaded into DuckDB.

## Entities

### Entity: Dataset
Metadata for an uploaded CSV (or, Phase 2, a registered Postgres connection treated as a source).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (uuid) | yes | Primary key |
| name | str | yes | Original filename / source label |
| source_type | str | yes | "csv" \| "postgres" |
| row_count | int | yes | Profiled locally |
| schema_summary | JSON (Text) | yes | Columns, types, scalar aggregates — the ONLY data shape sent to the LLM |
| created_at | timestamp | yes | Upload/connect time |

### Entity: Connection (Phase 2)
A registered PostgreSQL source.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (uuid) | yes | Primary key |
| label | str | yes | User-friendly name |
| connection_string | str | yes | Stored locally only; NEVER sent to the LLM |
| created_at | timestamp | yes | Registration time |

### Entity: Question
One asked question and its result.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (uuid) | yes | Primary key |
| dataset_id | str | yes | FK → Dataset |
| conversation_id | str | yes (Phase 4) | Groups follow-up turns |
| question | str | yes | The user's plain-English question |
| answer_text | str | no | Plain-English answer |
| chart_spec | JSON (Text) | no | `{type, x, series}` |
| status | str | yes | "completed" \| "failed" |
| error_message | str | no | On failure |
| created_at | timestamp | yes | Ask time |

### Entity: RunRow (existing)
Retained from the skeleton for run-level status (the runner writes status/error here). Question rows carry the domain result.

### Relationships
- Dataset 1—N Question. Connection 1—N Dataset (Phase 2, a Postgres connection is a Dataset of `source_type="postgres"`). Question N—1 conversation (Phase 4).

## The LLM-bound summary shape (the ONLY thing sent to the model)

```json
// schema_summary (plan_compute payload)
{
  "row_count": 12000,
  "columns": [
    {"name": "region", "type": "text", "distinct": 5, "nulls": 0},
    {"name": "revenue", "type": "number", "min": 0, "max": 98000, "nulls": 3}
  ]
}
// aggregate_result (phrase_answer payload) — bounded grouped result, NO raw rows
{
  "group_by": "region",
  "metric": "revenue",
  "aggregation": "sum",
  "rows": [{"region": "West", "revenue": 410000}, {"region": "East", "revenue": 380000}]
}
```

## Data Lifecycle

- Uploaded files + DuckDB tables exist for the session/personal use; they can be cleared without affecting metadata integrity. No remote backup or transmission.
- Question/Dataset metadata persists in SQLite until the user deletes it.
- Nothing is time-boxed or auto-archived (personal tool).

## Sensitive Data

- **Raw rows** (in DuckDB / uploaded files) and the **PostgreSQL connection string** are the sensitive surfaces. Both stay local; neither is ever sent to the LLM. The connection string is stored in the local SQLite store only. The `assert_no_raw_rows` guard enforces that only schema/aggregate payloads reach the LLM.
