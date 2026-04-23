# API

## API Style

REST over HTTP. Server-rendered HTML responses (Jinja2 templates) for browser-facing routes. JSON responses for the `/health` endpoint.

## Endpoints

### `GET /`

**Purpose:** Render the food photo upload form.

**Response:** HTML page with a file upload form.

---

### `POST /analyze`

**Purpose:** Accept a food photo upload, run the analysis pipeline, and render the result page.

**Request:** `multipart/form-data` with field `photo` (JPEG, PNG, HEIC — max 10 MB).

**Response:** HTML page displaying:
- Food name
- Estimated calories (kcal)
- Protein (g), Carbohydrates (g), Fat (g)
- Stub mode banner (visible when provider = `stub`)

**Error cases:**
| Status | Condition |
|--------|-----------|
| 400 | No file uploaded, or file exceeds 10 MB |
| 422 | Gemini returned a response that could not be parsed as nutrition data |
| 500 | Database write failed or Gemini returned an unexpected error |

---

### `GET /health`

**Purpose:** Health check — confirms the app is running.

**Response:**
```json
{"status": "ok"}
```

## Authentication

None in v0.1. Single-user local deployment.
