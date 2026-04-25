# Data Model

## Entities

### SourcingRun

Represents one end-to-end sourcing job triggered by a user.

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| project_name | VARCHAR(200) | User-provided |
| status | ENUM(pending, running, completed, failed) | Updated by agent |
| created_at | TIMESTAMP | Set at creation |
| completed_at | TIMESTAMP | Nullable; set when status=completed or failed |
| error_message | TEXT | Nullable; set if status=failed |

### MaterialLineItem

One material requested within a SourcingRun.

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| run_id | UUID | FK → SourcingRun.id |
| material_name | VARCHAR(200) | e.g. "Portland Cement" |
| quantity | DECIMAL(12,3) | Amount required |
| unit | VARCHAR(50) | e.g. "tonnes", "bags" |

### SupplierRecommendation

One ranked supplier candidate for one material in one run.

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| run_id | UUID | FK → SourcingRun.id |
| line_item_id | UUID | FK → MaterialLineItem.id |
| rank | INTEGER | 1 = best |
| supplier_name | VARCHAR(200) | |
| supplier_location | VARCHAR(200) | Nullable |
| price_per_unit | DECIMAL(12,2) | Estimated |
| currency | VARCHAR(10) | Default "USD" |
| lead_time_days | INTEGER | Estimated |
| certifications | TEXT | Comma-separated, nullable |
| score | DECIMAL(5,4) | Weighted score 0.0–1.0 |
| notes | TEXT | Nullable |

## Relationships

- SourcingRun 1 → N MaterialLineItem
- SourcingRun 1 → N SupplierRecommendation
- MaterialLineItem 1 → N SupplierRecommendation

## Data Lifecycle

1. SourcingRun created with status=pending when user submits form
2. Agent sets status=running at start of pipeline
3. MaterialLineItem rows created from form input
4. SupplierRecommendation rows created by rank_node
5. SourcingRun status set to completed (or failed)
6. Rows are never deleted in v0.1 (soft delete in future)
