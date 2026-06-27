# Data Model

## Storage Technology

SQLite via SQLAlchemy 2.0. Chosen for Phase 1 because the tool is personal and single-user; no network DB setup required. Phase 2 adds a PostgreSQL connection for live database queries (stored in .env, not in SQLite).

## Entities

### Entity: Dataset

Represents one uploaded CSV or Excel file. Created when the user uploads a file; never updated after creation. Deleted only if the user deletes the dataset (out of scope for Phase 1).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | TEXT (UUID4) | yes | Primary key, generated at upload time |
| filename | TEXT | yes | Original filename as uploaded by the user |
| file_path | TEXT | yes | Absolute path to the stored file: `{repo_root}/data/uploads/{id}_{filename}` |
| columns_json | TEXT | yes | JSON array of `{"name": str, "dtype": str}` objects, one per column; dtype is the pandas dtype string (e.g. "int64", "object", "float64") |
| sample_rows_json | TEXT | yes | JSON array of up to 20 row dicts (`df.head(20).to_dict(orient="records")`); used as the LLM context |
| row_count | INTEGER | yes | Total number of rows in the file (`len(df)`) |
| created_at | TIMESTAMP | yes | UTC timestamp of upload |

### Entity: Run

Represents one analysis execution. Exists in the boilerplate skeleton; columns extended to track analysis results.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | INTEGER | yes | Primary key, auto-increment |
| run_id | TEXT | yes | UUID string — matches the LangGraph run_id |
| dataset_id | TEXT | no | Foreign key to datasets.id; NULL for runs not associated with a dataset |
| question | TEXT | no | The user's plain-English question |
| chart_type | TEXT | no | "bar", "line", or "scatter" — set after successful analysis |
| status | TEXT | yes | "running", "completed", or "failed" |
| error_message | TEXT | no | Set when status is "failed" |
| created_at | TIMESTAMP | yes | UTC timestamp when the run started |
| completed_at | TIMESTAMP | no | UTC timestamp when the run completed or failed |

## Relationships

- A Run optionally references a Dataset (many-to-one: many Runs may reference the same Dataset)
- A Dataset may have zero or many Runs referencing it

## File Storage

Uploaded files are stored at: `{repo_root}/data/uploads/{dataset_id}_{filename}`

The `data/uploads/` directory is created at application startup if it does not exist. It is gitignored.

## Data Lifecycle

- Dataset rows are created on upload and are immutable after creation
- Run rows are created when POST /analyze is called (status = "running") and updated when the LangGraph graph completes (status = "completed" or "failed")
- No automatic expiry or archiving in Phase 1

## Sensitive Data

- Uploaded files may contain business or personal data — they are stored locally and never transmitted to Gemini in full
- Only the column schema and first 20 sample rows from `sample_rows_json` are sent to the Gemini API
- No authentication or access control in Phase 1 (personal tool, local only)
- `AGENT_GEMINI_API_KEY` is stored in `.env` (gitignored) — never logged, never committed
