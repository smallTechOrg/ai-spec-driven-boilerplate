# Code Style

## General
- Python 3.12, async throughout
- `src/prmonitor/` package layout
- Pydantic models for all domain objects and config
- Repository pattern for DB access — functions return domain models, never ORM rows
- All external calls in `tools/` — one file per integration

## Testing
- `tests/unit/` — mock all external calls
- `tests/integration/` — use real DB (in-memory SQLite for CI), stub HTTP
- Phase 2 gate test must pass with zero env vars set
