# Data Model

## Storage Technology

PostgreSQL 14+ via SQLAlchemy 2.0 (sync, psycopg2). Migrations with Alembic. Tests run against a separate `lead_gen_agent_test` database — never SQLite.

## Entities

### Entity: `Run`

Represents one operator-triggered pipeline execution.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | text (uuid) | yes | Primary key |
| filters | jsonb | yes | `{country, industry, size_band}` |
| status | text | yes | `pending` \| `completed` \| `failed` |
| error_message | text | no | Populated when `status=failed` |
| created_at | timestamptz | yes | Default `now()` |
| completed_at | timestamptz | no | Set when status transitions to completed/failed |

### Entity: `Lead`

One scored SMB candidate. Belongs to a `Run`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | text (uuid) | yes | Primary key |
| run_id | text | yes | FK → `runs.id` ON DELETE CASCADE, indexed |
| name | text | yes | Company name |
| website | text | no | Homepage URL |
| country | text | yes | EU country; indexed |
| industry | text | yes | Industry label; indexed |
| size_band | text | yes | One of `1-10`, `11-50`, `51-200`, `201-500` |
| hq_city | text | no | HQ city |
| description | text | no | One-line summary from extract node |
| score | integer | yes | 0–100 likelihood of lacking an in-house data function |
| rationale | text | no | One-sentence justification from score node |
| created_at | timestamptz | yes | Default `now()` |

### Relationships

- `Run` 1 — * `Lead` (cascade delete).

## Indexes

- `ix_leads_run_id` on `leads(run_id)`
- `ix_leads_country` on `leads(country)`
- `ix_leads_industry` on `leads(industry)`

## Enum-like constraints (application-enforced)

- `Run.status ∈ {pending, completed, failed}`
- `Lead.size_band ∈ {1-10, 11-50, 51-200, 201-500}`
- `Lead.country ∈ EU_COUNTRIES` (see `domain/models.py`)
- `0 ≤ Lead.score ≤ 100`

## Data Lifecycle

- Runs + leads are append-only in v0.1. No update/delete UI.
- Deleting a run cascades to its leads (for future admin CLI — not exposed in v0.1).

## Sensitive Data

No PII. Lead data is public firmographic information (company name, website, city). API keys live in environment variables only (never persisted).
