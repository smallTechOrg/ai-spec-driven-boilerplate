# Data Model

App-state entities for the Local Data Analyst. **App state lives in SQLite** (SQLAlchemy 2.0 + Alembic). **The actual user file data lives in DuckDB** (the local query engine) — DuckDB holds the rows; SQLite holds only metadata, history, and audit. Raw rows never leave the machine.

---

## Storage Technology

- **SQLite** (via SQLAlchemy 2.0 + Alembic, `AGENT_DATABASE_URL`) — app state: the dataset library, conversation history, and the audit trail of every run. Small, structured, single-user.
- **DuckDB** — the query engine over the user's CSV/Excel data. Each dataset is loaded as a DuckDB table. In Phase 1, DuckDB is in-process and the dataset is loaded per request from the stored file path; in Phase 2, datasets persist on disk per dataset for cross-day reuse. **DuckDB stores the raw rows; SQLite never does.**

The two stores are separate: SQLAlchemy models below describe SQLite only. DuckDB tables are described by their `Dataset` metadata row, not by an ORM model.

## Entities

### Entity: Dataset (library entry)

A single loaded dataset (one CSV file, or one Excel sheet). Lives in SQLite as metadata; its rows live in DuckDB.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Text (uuid) | yes | Primary key |
| name | Text | yes | Display name (filename, or `file.xlsx — SheetName`) |
| source_path | Text | yes | Absolute path to the stored source file on disk |
| source_kind | Text | yes | `csv` or `excel` |
| sheet_name | Text | no | Excel sheet name (null for CSV) |
| duckdb_table | Text | yes | The DuckDB table name the rows are loaded into |
| profile_json | Text (JSON) | no | Cached profile: rows, columns+types, null counts, basic stats |
| row_count | Integer | no | Cached row count from profiling |
| size_bytes | Integer | no | Source file size |
| created_at | TIMESTAMP(tz) | yes | When loaded |
| updated_at | TIMESTAMP(tz) | yes | Last touched |

### Entity: Run (audit record)

One row per ask — the full audit trail. This is the existing `runs` table extended with data-analyst fields (extend the model in place; add columns via Alembic migration `0002`).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Text (uuid) | yes | Primary key (`run_id`) |
| dataset_id | Text (FK → Dataset.id) | no | Dataset queried (null if upload-only) |
| status | Text | yes | `pending` / `completed` / `failed` |
| question | Text | no | The user's plain-English question |
| plan_json | Text (JSON) | no | The plan steps |
| generated_sql | Text | no | The DuckDB SQL that ran (or was attempted) |
| result_summary_json | Text (JSON) | no | The aggregates + narration summary (NOT raw rows) |
| prompt_tokens | Integer | no | Summed prompt tokens |
| completion_tokens | Integer | no | Summed completion tokens |
| est_usd | Float | no | Estimated USD cost for the run |
| error_message | Text | no | Failure reason (with attempted SQL preserved) |
| created_at | TIMESTAMP(tz) | yes | Run start |
| updated_at | TIMESTAMP(tz) | yes | Run end / last update |

> The skeleton's `RunRow` currently has `input_text`/`output_text`. These are repurposed/renamed in migration `0002` (`input_text` → `question`, `output_text` → `result_summary_json`) and the new columns above are added. Generators MUST extend the existing `runs` table, not create a parallel one.

### Entity: Message (conversation history)

One row per conversation turn, so follow-ups have context and history restores across days (Phase 2 surfaces restore; the table is created in Phase 1).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Text (uuid) | yes | Primary key |
| session_id | Text (FK → Session.id) | no | Owning session (null until Phase 2 sessions) |
| dataset_id | Text (FK → Dataset.id) | no | Dataset the turn was about |
| run_id | Text (FK → Run.id) | no | The run that produced an assistant turn |
| role | Text | yes | `user` or `assistant` |
| content | Text | yes | The question (user) or the answer text (assistant) |
| created_at | TIMESTAMP(tz) | yes | Turn time |

### Entity: Session (cross-day restore — modelled now, surfaced Phase 2)

A workspace session so the user resumes where they left off. Created in Phase 1's migration but only actively used from Phase 2.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Text (uuid) | yes | Primary key |
| active_dataset_id | Text (FK → Dataset.id) | no | The last-loaded dataset |
| created_at | TIMESTAMP(tz) | yes | Session start |
| updated_at | TIMESTAMP(tz) | yes | Last activity |

> **Assumed:** Phase 1 may run with a single implicit/default session; the `Session` row is created so Phase 2 restore needs no schema change. Modelling it now avoids a later migration churn.

## Relationships

- `Dataset` 1 ─ N `Run` (a dataset has many runs).
- `Dataset` 1 ─ N `Message`.
- `Session` 1 ─ N `Message`; `Session` N ─ 1 `Dataset` (active dataset).
- `Run` 1 ─ 1 assistant `Message` (the run that produced it).

## Data Lifecycle

- **Create:** `Dataset` on upload; `Run` + `Message`s on each ask; `Session` on first use / restored on boot (Phase 2).
- **Update:** `Dataset.profile_json` cached at profile time; `Run` updated at finalize/handle_error.
- **Delete:** the user can delete a library `Dataset` (Phase 2), which drops its DuckDB table and orphan-cleans its source file; Runs/Messages are retained for audit unless the user explicitly clears history.
- **Persistence of file data:** Phase 1 keeps the source file on disk and (re)loads the DuckDB table per request; Phase 2 persists DuckDB tables on disk per dataset so reload is instant and survives restart.

## Sensitive Data

- **Raw data rows are the sensitive asset.** They live ONLY in DuckDB / the on-disk source file on the user's machine. They are NEVER written to an LLM prompt and NEVER sent to any remote service. SQLite stores only metadata, aggregates, and narration — never raw rows.
- The Gemini API key is a secret, read from `.env` (`AGENT_GEMINI_API_KEY`); it is never logged or returned in any API response.
- `Run.result_summary_json` stores aggregates + narration only (capped, summarized) — verify in code review that no full raw-row dump is persisted there.
