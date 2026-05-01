# Data Model

## Storage Technology

PostgreSQL. Managed via SQLAlchemy 2.0 (declarative `Mapped` types) and Alembic for migrations. A single `food_logs` table holds every analysis result.

## Entities

### Entity: FoodLog

One row per food photo analysis. Created on every successful call to `POST /analyze`. Never updated or deleted in v0.1.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | integer (PK, autoincrement) | yes | Primary key |
| analyzed_at | timestamp with time zone | yes | When the analysis was run (UTC, server time) |
| image_filename | varchar(255) | yes | Original filename of the uploaded photo |
| food_name | varchar(255) | yes | Name of the identified food (e.g. "Caesar salad") |
| calories_kcal | numeric(8,2) | yes | Estimated total calories |
| protein_g | numeric(8,2) | yes | Estimated protein in grams |
| carbs_g | numeric(8,2) | yes | Estimated carbohydrates in grams |
| fat_g | numeric(8,2) | yes | Estimated fat in grams |
| provider | varchar(50) | yes | LLM provider used: `"gemini"` or `"stub"` |

### Relationships

No relationships. `FoodLog` is the only entity in v0.1.

## Data Lifecycle

- **Created:** immediately after a successful Gemini (or stub) analysis
- **Updated:** never
- **Deleted:** never in v0.1 (no purge or archive logic)

## Sensitive Data

No PII in the `food_logs` table. Image bytes are not persisted to the database — only the original filename is stored. The Gemini API key is kept in `.env` only and never written to the database or logs.
