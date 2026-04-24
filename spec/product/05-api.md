# API

## API Style

Mixed: browser-facing HTML routes (Jinja2 templates) + one CSV streaming endpoint. No JSON API in v0.1.

## Endpoints

### `GET /`

Renders the home page with the run-trigger form (country, industry, size_band selects).

### `GET /health`

Returns `{"status": "ok"}`. Used for liveness checks (required by Phase 2 gate).

### `POST /runs`

Triggers a new pipeline run. Form fields: `country`, `industry`, `size_band`.
- On success: 303 redirect to `/runs`.
- On validation error: re-renders `/` with the error message in the banner area.

### `GET /runs`

Lists all runs (most recent first): id, filters, status, created_at, lead count.

### `GET /leads`

Renders the ranked leads table. Query params (all optional): `country`, `industry`, `size_band`, `min_score`. Default order: score desc, then created_at desc.

### `GET /leads.csv`

Streams the current filtered leads view as CSV (same query params as `/leads`).
- `Content-Type: text/csv`
- `Content-Disposition: attachment; filename="leads.csv"`
- Columns: `name, website, country, industry, size_band, hq_city, score, rationale, description`

## Error Cases

| Status | Condition |
|--------|-----------|
| 400 | Invalid filter (unknown country / size_band) |
| 500 | Unhandled exception — rendered as error page, never raw JSON |

## Authentication

None in v0.1. Single-operator local tool.
