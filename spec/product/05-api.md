# API

## API Style

REST (FastAPI). Also serves the dashboard HTML. All data endpoints return JSON. Base path: `http://localhost:8000`.

---

## Blog Configuration

### `GET /blog`
Returns the current blog configuration.

**Response:**
```json
{
  "id": 1,
  "name": "The Curious Mind",
  "tagline": "AI ideas for curious people",
  "niche": "AI tools for solopreneurs",
  "themes": ["productivity", "automation", "no-code"],
  "posts_per_run": 3,
  "schedule_cron": "0 8 * * 1",
  "output_dir": "./output"
}
```

### `PUT /blog`
Update blog configuration.

**Request:** Same shape as response above (all fields optional except `name` and `niche`).

**Error cases:**
| Status | Condition |
|--------|-----------|
| 422 | Invalid cron expression |
| 422 | `posts_per_run` < 1 or > 10 |

---

## Writers

### `GET /writers`
Returns all writers (active and inactive).

**Response:** `{ "writers": [ Writer, ... ] }`

### `POST /writers`
Create a new writer.

**Request:**
```json
{
  "name": "Alex Chen",
  "persona_prompt": "You are Alex Chen, a pragmatic engineer who explains complex AI concepts with real-world examples...",
  "bio": "Alex is a software engineer who loves making AI tools accessible to non-technical founders.",
  "avatar_url": null
}
```

**Response:** Created `Writer` object.

**Error cases:**
| Status | Condition |
|--------|-----------|
| 422 | `name` or `persona_prompt` or `bio` missing |
| 409 | Writer with same name already exists |

### `PUT /writers/{id}`
Update an existing writer.

### `DELETE /writers/{id}`
Deactivate a writer (sets `is_active = false`). Does not delete records.

---

## Runs

### `GET /runs`
Returns run history, newest first.

**Response:** `{ "runs": [ Run, ... ] }`

### `POST /runs/trigger`
Manually trigger a generation run.

**Request:**
```json
{ "posts_count": 3 }
```
`posts_count` is optional; defaults to blog's `posts_per_run`.

**Response:**
```json
{ "run_id": 42, "status": "running" }
```

**Error cases:**
| Status | Condition |
|--------|-----------|
| 409 | A run is already in progress |
| 422 | No active writers configured |
| 422 | Blog not configured (niche is empty) |

### `GET /runs/{id}`
Returns a single run with its posts.

**Response:**
```json
{
  "id": 42,
  "trigger": "manual",
  "status": "completed",
  "posts_requested": 3,
  "posts_completed": 3,
  "started_at": "2026-04-23T08:00:00Z",
  "completed_at": "2026-04-23T08:03:14Z",
  "posts": [ Post, ... ]
}
```

---

## Posts

### `GET /posts`
Returns all posts, newest first.

**Query params:**
- `limit` (default 20)
- `offset` (default 0)
- `writer_id` (optional filter)

---

## Dashboard (HTML)

### `GET /`
Serves the main dashboard HTML page (single-page app in vanilla JS).

All dashboard interactions use the REST endpoints above via `fetch()`.
