# Data Model

## Storage Technology

PostgreSQL 14+ via SQLAlchemy 2.0 (psycopg2 driver). Migrations managed with
Alembic. The same database engine is used in tests — SQLite is **not** a
substitute (per `spec/engineering/ai-agents.md` rule 5).

## Entities

### SourcingRequest

The user's input — what they want to source.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID (text) | yes | Primary key |
| material | text | yes | e.g. "red clay brick", "OPC 53 cement" |
| quantity | text | yes | Free-form ("10000 units", "200 bags") |
| location | text | yes | Delivery city / region |
| budget | text | no | Free-form budget hint |
| timeline | text | no | Free-form timeline hint |
| criteria | text | no | Quality / preference criteria |
| created_at | timestamptz | yes | Server time |

### Run

One execution of the sourcing graph for a given request.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID (text) | yes | Primary key |
| request_id | UUID (text) | yes | FK → sourcing_requests.id |
| status | text | yes | pending / running / completed / failed |
| llm_provider | text | yes | Resolved provider name at run time (`gemini` / `stub`) |
| search_provider | text | yes | Resolved provider name at run time (`tavily` / `stub`) |
| error_message | text | no | Populated when status = failed |
| created_at | timestamptz | yes | Server time |
| updated_at | timestamptz | yes | Auto-bumped |

### Supplier

A candidate supplier surfaced during research and enriched by the LLM.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID (text) | yes | Primary key |
| run_id | UUID (text) | yes | FK → runs.id |
| name | text | yes | Supplier company name |
| location | text | no | Supplier city / region |
| price_indication | text | no | "₹6.50 / brick" etc. |
| lead_time | text | no | "5–7 days" etc. |
| source_url | text | no | Where we found them |
| notes | text | no | Free-form enrichment notes |

### Recommendation

A scored ranking of one supplier for one run.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID (text) | yes | Primary key |
| run_id | UUID (text) | yes | FK → runs.id |
| supplier_id | UUID (text) | yes | FK → suppliers.id |
| rank | integer | yes | 1 = best |
| score | integer | yes | 0–100 |
| rationale | text | yes | One paragraph explanation |

## Relationships

- `SourcingRequest 1—N Run` (a request can be re-run)
- `Run 1—N Supplier`
- `Run 1—N Recommendation` (ordered by `rank`)
- `Supplier 1—1 Recommendation` (per run)

## Data Lifecycle

- All rows are append-only in v0.1; no deletes, no archive.
- Time-zone-aware timestamps, UTC.
