# Data Model

Persistence is SQLite (`sqlite:///./data/agent.db`) via SQLAlchemy + Alembic. The raw uploaded
file lives on the local filesystem (`data/uploads/<dataset_id>.<ext>`), NOT in the database —
only metadata, schema, sample, and query records are stored.

## Entities

### Dataset (`DatasetRow`, table `datasets`)
One uploaded file.

| Field | Type | Notes |
|-------|------|-------|
| id | str (uuid) PK | also the local filename stem |
| filename | str | original upload name |
| source_format | str | `"csv"` (Phase 1); `"xlsx"` from Phase 3 |
| file_path | str | local path `data/uploads/<id>.<ext>` (data stays local) |
| row_count | int | rows in the loaded DataFrame |
| schema_json | JSON | `[{name, dtype}, ...]` derived locally |
| sample_json | JSON | bounded `{preview_rows, summary}` (first N rows + per-column stats) |
| size_bytes | int | upload size (enforced against `max_upload_mb`) |
| created_at | timestamp | |

### Query (`QueryRow`, table `queries`)
One question asked against a dataset, with the captured computation — the auditable record.

| Field | Type | Notes |
|-------|------|-------|
| id | str (uuid) PK | |
| dataset_id | str FK → datasets.id | indexed |
| conversation_id | str | = dataset_id from Phase 2 (session memory key); blank in P1 |
| question | str | the natural-language question |
| code | str (nullable) | the exact pandas the agent executed (show-its-work) |
| result_json | JSON (nullable) | the captured numeric result |
| explanation | str (nullable) | plain-language explanation |
| answer | str (nullable) | human-readable numeric answer string |
| status | str | `"completed"` \| `"failed"` |
| error_message | str (nullable) | human-readable failure |
| repair_attempts | int | sandbox repair retries used |
| tokens_in / tokens_out | int (nullable) | observability |
| cost_usd / latency_ms | float (nullable) | observability |
| model | str (nullable) | e.g. `gemini-2.5-flash` |
| node_trace | JSON (nullable) | per-node timing |
| guard_code | str (nullable) | machine-readable guard verdict |
| created_at | timestamp | |

### (Existing) `TurnRow` (table `turns`)
Reused from the baseline for Phase 2 multi-turn memory, keyed by `conversation_id` (= the
`dataset_id`). One row per conversation turn (role + content). Dormant in Phase 1.

> The baseline `RunRow`/`FactRow` tables and `transform_text` capability are superseded by the
> analysis capability; `RunRow` may remain in the schema but is off the analysis path.

## Relationships
- `Dataset` 1 ──< `Query` (a dataset has many queries).
- `Query.conversation_id` groups multi-turn queries on the same dataset (Phase 2) and keys
  `TurnRow` rows.

## Lifecycle
1. Upload → `DatasetRow` created; file written to `data/uploads/`; schema+sample derived and
   persisted.
2. Ask → graph runs → `QueryRow` created with question, code, result, explanation, status, and
   observability fields.
3. Failure → `QueryRow` persisted with `status="failed"` + human-readable `error_message`.
4. No deletion/retention policy in v1 (single-user local tool).
