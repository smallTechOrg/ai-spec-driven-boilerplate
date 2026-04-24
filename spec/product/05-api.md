# API

## API Style

REST — server-rendered HTML pages (Jinja2) plus JSON endpoints for run status polling. No external API clients; all callers are the browser.

## Endpoints

### `GET /`

**Purpose:** Render the main dashboard — list of leads with filter controls.

**Response:** HTML page.

### `GET /health`

**Purpose:** Health check for live-server smoke test.

**Response:**
```json
{ "status": "ok" }
```

### `GET /runs/new`

**Purpose:** Render the new-search form.

**Response:** HTML page.

### `POST /runs`

**Purpose:** Create and execute a new search run.

**Request (form data):**
| Field | Type | Required |
|-------|------|----------|
| country | str | yes |
| industry | str | yes |
| size_min | int | no |
| size_max | int | no |

**Response:** Redirect to `/runs/{id}` (303 See Other).

**Error cases:**
| Status | Condition |
|--------|-----------|
| 422 | Missing required field |
| 500 | Pipeline run failed |

### `GET /runs/{run_id}`

**Purpose:** Show results page for a completed run.

**Response:** HTML page with lead table and CSV export link.

### `GET /leads/export.csv`

**Purpose:** Download all current leads as a CSV file.

**Response:** `text/csv` attachment.

**Query params:**
| Param | Description |
|-------|-------------|
| country | Filter by country |
| industry | Filter by industry |
| status | Filter by lead status |

## Authentication

No authentication in v0.1. The app is local-only; no public exposure.
