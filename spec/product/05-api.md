# API / HTTP Surface

The app is server-rendered HTML. There are no JSON APIs in v0.1.

## Routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Render new sourcing request form |
| POST | `/requests` | Create request + run, invoke agent, redirect to `/runs/{id}` |
| GET | `/runs/{run_id}` | Render report (ranked recommendations + supplier details) |
| GET | `/runs` | List recent runs (most recent first) |
| GET | `/health` | Liveness probe — JSON `{"status": "ok"}` |

## Form fields (POST /requests)

- `material` (required, str)
- `quantity` (required, str)
- `location` (required, str)
- `budget` (optional, str)
- `timeline` (optional, str)
- `criteria` (optional, str)

## Error rendering

Any node raising in the graph sets `run.status = "failed"` and
`run.error_message`. The report page renders the error inline (red panel),
not a 500.
