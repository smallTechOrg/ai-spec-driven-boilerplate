# Data Model

## Storage Technology

PostgreSQL via SQLAlchemy 2.0 (Mapped / declarative) + Alembic migrations. Chosen for relational integrity and easy CSV export queries.

## Entities

### Entity: SearchRun

Represents one invocation of the discovery pipeline. Tracks input criteria and outcome.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID (str) | yes | Primary key |
| country | str | yes | ISO-3166-1 alpha-2 country code (e.g. `DE`) |
| industry | str | yes | Free-text industry/sector (e.g. `retail`) |
| size_min | int | no | Minimum employee headcount |
| size_max | int | no | Maximum employee headcount |
| status | str | yes | `running` \| `completed` \| `failed` |
| error_message | str | no | Set when status = `failed` |
| lead_count | int | no | Number of leads discovered in this run |
| created_at | datetime (UTC) | yes | Run start timestamp |
| completed_at | datetime (UTC) | no | Run end timestamp |

### Entity: Lead

Represents one discovered company and its enrichment data.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID (str) | yes | Primary key |
| search_run_id | UUID (str) | yes | FK → SearchRun.id |
| company_name | str | yes | Company display name |
| domain | str | yes | Website domain (unique index — dedup key) |
| website | str | no | Full URL |
| country | str | yes | Country where headquartered |
| industry | str | no | Industry / sector |
| headcount_estimate | str | no | Headcount band (e.g. `10–50`) |
| why_fit | str | no | 2-sentence AI-generated reason this company fits the pitch |
| status | str | yes | `new` \| `contacted` \| `rejected` |
| created_at | datetime (UTC) | yes | When the lead was first stored |

### Relationships

One `SearchRun` has many `Lead` records (1:N). A `Lead` always belongs to the run that first discovered it. Dedup is enforced at the `domain` level — if a domain is re-discovered in a later run, it is not re-inserted (upsert / ignore-on-conflict).

## Data Lifecycle

- `SearchRun` records are created immediately when the user submits the form; status transitions `running → completed | failed`.
- `Lead` records persist indefinitely; status can be manually updated in the dashboard.
- No automated deletion in v0.1.

## Sensitive Data

v0.1 stores firmographic data only (company-level). No personal names, personal emails, or phone numbers are stored. GDPR Article 4 "personal data" does not apply to company-level firmographics. The `domain` field is a business identifier, not a personal identifier.
