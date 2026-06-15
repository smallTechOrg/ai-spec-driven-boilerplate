# API

## API Style

REST (FastAPI) + Server-rendered HTML (Jinja2). Browser UI is the primary surface; JSON endpoints support future integration.

## Endpoints

### `GET /`

**Purpose:** Render the upload form (home page).

**Response:** HTML — upload form

---

### `POST /upload`

**Purpose:** Accept a CSV file, store it on disk, create a Dataset record in SQLite.

**Request:** `multipart/form-data` with field `file` (CSV)

**Response:** Redirect to `GET /datasets/{id}`

**Error cases:**
| Status | Condition |
|--------|-----------|
| 400 | No file provided or file is not CSV |
| 500 | Disk write failed |

---

### `GET /datasets/{dataset_id}`

**Purpose:** Show the dataset detail page with column names, row count, and query form.

**Response:** HTML

**Error cases:**
| Status | Condition |
|--------|-----------|
| 404 | Dataset not found |

---

### `POST /datasets/{dataset_id}/query`

**Purpose:** Submit a natural language question. Triggers LangGraph pipeline. Returns answer page on completion.

**Request:** `application/x-www-form-urlencoded` with field `question`

**Response:** HTML — answer page with question, answer, and "Ask another" link

**Error cases:**
| Status | Condition |
|--------|-----------|
| 400 | Empty question |
| 404 | Dataset not found |
| 500 | Pipeline error — renders error.html with detail |

---

### `GET /datasets/{dataset_id}/history`

**Purpose:** Show all past queries for a dataset.

**Response:** HTML — list of questions and answers

---

### `GET /health`

**Purpose:** Health check — returns 200 with `{"status": "ok"}`.

**Response:**
```json
{"status": "ok"}
```

## Authentication

None in v0.1. Single-user local deployment.
