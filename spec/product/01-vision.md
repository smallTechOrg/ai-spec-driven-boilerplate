# Vision

## What This Agent Does

Food Tracker is a web-based agent that lets a user upload a photo of their food and instantly receive a nutrition breakdown: the name of the food, estimated calories, and protein/carbohydrate/fat macros. Every analysis is logged to a PostgreSQL database for reference. The agent uses Google Gemini Vision to interpret the photo and extract structured nutrition data.

## Who Uses It

Any individual who wants to track what they eat without manually looking up nutrition facts. The user opens a browser, uploads a food photo, and sees the result on the same page within seconds.

## Core Problem Being Solved

Manual calorie and macro tracking is tedious — users must identify every ingredient, weigh portions, and cross-reference a database. This agent replaces that friction with a single photo upload, cutting the effort from minutes to seconds.

## Success Criteria

- [ ] Uploading a food photo returns a food name, calorie estimate, and protein/carbs/fat within 5 seconds
- [ ] Every analysis result is persisted to PostgreSQL with a timestamp
- [ ] The web UI clearly labels when the Gemini provider is stubbed (offline/demo mode)
- [ ] The full pipeline runs end-to-end in stub mode without any API key (Phase 2 gate)
- [ ] Real Gemini Vision returns a sensible result for a clear food photo (Phase 3 gate)

## What This Agent Does NOT Do (Out of Scope)

- Micronutrient breakdown (vitamins, minerals, sodium, fibre) — deferred to future
- Daily totals or history dashboard — deferred to future
- User authentication or multi-user support — deferred to future
- Barcode or label scanning — deferred to future
- Manual food entry (text-only, no photo) — deferred to future
- Meal planning or recommendations — out of scope indefinitely

## Key Constraints

- LLM provider: Google Gemini Vision (`gemini-2.0-flash`) — user has the API key
- Database: PostgreSQL, runs locally
- Language: Python 3.12, runs locally
- Port: 8001 (not 8000)
- Gemini model name must be configurable via `FOOD_TRACKER_LLM_MODEL` env var
- No secrets in source code; all credentials in `.env`

## Phases of Development

| Phase | Description | Success Gate |
|-------|-------------|--------------|
| 1 | Domain models + PostgreSQL schema + CRUD unit tests | `uv run alembic upgrade head` succeeds; `uv run pytest tests/unit/` passes |
| 2 | FastAPI web UI + stubbed Gemini pipeline, full end-to-end | `uv run pytest tests/` passes; live `/health` returns 200; stub banner visible |
| 3 | Real Gemini Vision integration replaces stub | Happy-path test with real food photo returns structured nutrition data |

## Future Phases

- Micronutrient detail (fibre, sodium, vitamins, minerals)
- Daily intake log with totals and macro pie chart
- User authentication (single-user passphrase or OAuth)
- Historical trends (weekly/monthly view)
- Barcode scanning via camera
