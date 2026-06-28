# Data Model — DataChat

---

## Storage Technology

**SQLite** (file `data/agent.db`) via **SQLAlchemy 2.0** ORM with **Alembic** migrations. SQLite is the production database for this single-user local tool, so tests run against SQLite too (no PostgreSQL anywhere). Uploaded spreadsheet **files** are stored on the local filesystem under `data/uploads/<dataset_id>/`; the database stores only metadata, profiles, conversations, messages, and run history — **never the raw rows**. All ids are UUID strings; all timestamps are timezone-aware UTC.

## Entities

### Entity: Dataset  *(P1; multi-file P4)*
A spreadsheet (or, P4, a group of similarly-shaped files / a folder) the user uploaded into the library.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (UUID) PK | yes | Dataset id |
| name | str | yes | Display name (original filename or user label) |
| kind | str | yes | `csv` \| `xlsx` (P4: `group` for multi-file) |
| file_path | str | yes | Local path under `data/uploads/<id>/` |
| row_count | int | yes | Rows (set at profile time) |
| column_count | int | yes | Columns |
| size_bytes | int | yes | File size |
| member_paths | JSON text | no | P4: list of file paths when `kind=group` |
| created_at | timestamptz | yes | Upload time |
| updated_at | timestamptz | yes | Last touched |

### Entity: DatasetProfile  *(P1; quality flags P3)*
The auto-generated schema/profile of a dataset — the safe, row-free summary the LLM is allowed to see.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (UUID) PK | yes | Profile id |
| dataset_id | str FK→datasets.id | yes | Owning dataset |
| columns | JSON text | yes | `[{name, dtype, non_null, n_unique, min, max, sample_values}]` — metadata, not rows |
| row_count | int | yes | Rows profiled |
| quality_flags | JSON text | no | P3: `[{column, issue: "nulls"|"dupes"|"outliers", detail}]` |
| created_at | timestamptz | yes | Profiled at |

### Entity: Conversation  *(P2)*
A multi-turn chat thread against one dataset.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (UUID) PK | yes | Conversation id |
| dataset_id | str FK→datasets.id | yes | Dataset under analysis |
| title | str | no | Auto/short title (first question) |
| created_at | timestamptz | yes | Started |
| updated_at | timestamptz | yes | Last message |

### Entity: Message  *(P2)*
One turn in a conversation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (UUID) PK | yes | Message id |
| conversation_id | str FK→conversations.id | yes | Thread |
| role | str | yes | `user` \| `assistant` |
| content | str | yes | Question text (user) or prose answer (assistant) |
| run_id | str FK→analysis_runs.id | no | The run that produced an assistant message |
| created_at | timestamptz | yes | Turn time |

### Entity: AnalysisRun  *(P1; conversation link P2)*
One executed question: the durable record of what was asked, the code that ran, the result, and the cost. This is the **full run history**.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (UUID) PK | yes | Run id |
| dataset_id | str FK→datasets.id | yes | Dataset analysed |
| conversation_id | str FK→conversations.id | no | P2: owning thread |
| question | str | yes | The natural-language question |
| plan | str | no | Plan text |
| code | str | no | Final pandas code that ran |
| result_summary | JSON text | no | Bounded computed result (scalars / small table / shape) — **never full raw rows** |
| answer | str | no | Prose answer |
| assumptions | JSON text | no | P3: flagged assumptions / uncertainty |
| followups | JSON text | no | P3: 2–3 suggested follow-ups |
| viz | JSON text | no | P4: chart/table spec |
| prompt_tokens | int | yes | Accumulated prompt tokens (default 0) |
| completion_tokens | int | yes | Accumulated completion tokens |
| total_tokens | int | yes | Sum |
| cost_usd | float | yes | Estimated cost (default 0.0) |
| status | str | yes | `pending` \| `completed` \| `failed` |
| error_message | str | no | Set on failure |
| created_at | timestamptz | yes | Asked at |
| completed_at | timestamptz | no | Finished at |

### Entity: RunStep  *(P3)*
One step of the bounded plan→code→execute→inspect loop — powers the step timeline and the transparency of self-correction.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (UUID) PK | yes | Step id |
| run_id | str FK→analysis_runs.id | yes | Owning run |
| step_index | int | yes | 0-based order |
| phase | str | yes | `planning` \| `generating_code` \| `running_code` \| `checking_result` |
| code | str | no | Code for this step |
| result_summary | JSON text | no | Bounded result/error for this step |
| error | str | no | Captured code error, if any |
| started_at | timestamptz | yes | Step start |
| ended_at | timestamptz | no | Step end |

## Relationships

- `Dataset 1—1 DatasetProfile` (latest profile per dataset; re-profile replaces).
- `Dataset 1—* Conversation`; `Conversation 1—* Message`.
- `Dataset 1—* AnalysisRun`; `Conversation 1—* AnalysisRun`; `AnalysisRun 1—* RunStep`.
- `Message 0..1—1 AnalysisRun` (assistant messages link to their run).

## Lifecycle

1. **Upload** → `Dataset` row + file on disk → profiler writes `DatasetProfile` (P3: with `quality_flags`).
2. **Ask** → `AnalysisRun` (`pending`) → graph runs → `RunStep`s (P3) → run updated to `completed`/`failed` with code, result, answer, tokens, cost.
3. **Conversation** (P2) → `user` `Message` + `assistant` `Message` linked to the run; `history` for the next turn is built from prior runs' `{question, result_summary}`.
4. **Persistence** → everything survives restart (SQLite + files); the library, conversations, and run history are all re-loadable.

## Migrations

| Revision | Phase | Adds |
|----------|-------|------|
| `0001` | (skeleton) | `runs` (legacy; retained) |
| `0002_datachat` | P1 | `datasets`, `dataset_profiles`, `analysis_runs` |
| `0003_conversations` | P2 | `conversations`, `messages`; `analysis_runs.conversation_id` |
| `0004_run_steps` | P3 | `run_steps`; `dataset_profiles.quality_flags`; run `assumptions`/`followups` |
| `0005_multifile` | P4 | `datasets.member_paths`; `analysis_runs.viz` |
