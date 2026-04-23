# Data Model

## Storage Technology

PostgreSQL 15+ via SQLAlchemy 2.0 + Alembic.

## Entities

### Voice
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | uuid | yes | PK |
| name | str (unique) | yes | Display name |
| description | str | yes | One-liner about the voice |
| guidelines | text | yes | Markdown — do's and don'ts |
| created_at | timestamptz | yes | |

### Writer
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | uuid | yes | PK |
| name | str | yes | Display name |
| persona | text | yes | Markdown — background/expertise |
| voice_id | uuid FK → voice.id | yes | |
| created_at | timestamptz | yes | |

### Article
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | uuid | yes | PK |
| writer_id | uuid FK → writer.id | yes | |
| voice_id | uuid FK → voice.id | yes | Denormalized for history |
| topic | str | yes | |
| title | str | yes | |
| body | text | yes | Markdown |
| created_at | timestamptz | yes | |

### AgentRun
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | uuid | yes | PK |
| article_id | uuid FK, nullable | no | Null on failure |
| writer_id | uuid FK | yes | |
| topic | str | yes | |
| status | enum(pending,completed,failed) | yes | |
| error_message | text | no | |
| created_at | timestamptz | yes | |

## Relationships

- Voice 1 — N Writer
- Writer 1 — N Article
- Writer 1 — N AgentRun

## Data Lifecycle

No automatic deletion. User deletes manually (future).

## Sensitive Data

None in v0.1.
