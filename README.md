# Private Data-Analysis Workbench

> All commands below are run from the **repo root**.

A single-user, local web app for asking natural-language questions of your own
spreadsheets. You upload a CSV, the app auto-profiles it, and an agent **writes
and runs pandas code locally against the full file** to answer your question —
showing its plan and the exact generated code.

**Privacy invariant (non-negotiable):** raw data rows never leave the server.
Analysis code runs locally against the full dataset; the LLM (Google Gemini) only
ever receives column schema, dtypes, basic aggregate stats, and a tiny sample of
at most 5 rows. Enforced in `src/analysis/profile.py` (`MAX_SAMPLE_ROWS = 5`) and
asserted by `tests/phase1/test_privacy_invariant.py`.

## Stack

- Python 3.12 + FastAPI (port 8001), single-origin static Next.js export at `/app/`.
- LangGraph agent (`src/graph/`): plan → generate_code → execute_code →
  inspect_result → (refine loop) → answer → finalize.
- Google Gemini (`gemini-2.5-flash` by default) via `google-genai`.
- pandas / numpy for local profiling + execution.
- SQLite + SQLAlchemy 2.0 (the production DB for this single-user app), Alembic
  migrations.

## Environment

Create a `.env` in the repo root:

```
AGENT_GEMINI_API_KEY=<your-gemini-api-key>
AGENT_LLM_MODEL=gemini-2.5-flash
AGENT_DATABASE_URL=sqlite:///./data/agent.db
```

- `AGENT_GEMINI_API_KEY` — required; the key lives only in `.env`, never in code.
- `AGENT_LLM_MODEL` — optional; defaults to `gemini-2.5-flash` when blank.
- `AGENT_DATABASE_URL` — optional; defaults to `sqlite:///./data/agent.db`.

## Run (Phase 1)

```
cd frontend && pnpm build
cd .. && uv run alembic upgrade head
uv run alembic current          # should print: 0002 (head)
uv run python -m src            # serves on http://0.0.0.0:8001
```

Then open **http://localhost:8001/app/**.

Drag a CSV (e.g. a sales export with thousands of rows) into the upload area; a
profile card appears within a few seconds (column names, dtypes, row count,
ranges, missing-value counts). Type a question such as *"what is the total
revenue by region?"* — a plain-English answer appears; expand "Show code" to see
the actual pandas and "Show plan" to see the agent's plan.

## Phase-1 endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/datasets` | Upload one CSV (`multipart/form-data`, field `file`); profile + persist. |
| `GET`  | `/datasets/{id}` | Fetch a dataset's metadata + profile. |
| `POST` | `/ask` | Ask a question; run the agent; return answer + code + plan. |
| `GET`  | `/health` | Liveness check. |

All responses use the envelope `{"data": ..., "error": null}` on success and
`{"detail": {"code", "message"}}` on error.

## What's real vs stub (Phase 1)

**Real, end-to-end on the core path:**
- CSV upload → on-disk persistence under `uploads/<dataset_id>/` → privacy-safe
  profiling.
- `POST /ask` → real Gemini plan/code/inspect/answer + real pandas execution
  against the **full** file, with a capped refine loop.
- Persistence of datasets, conversations, messages, and analysis runs in SQLite.

**Labelled "coming soon" stubs (later phases):**
- Dataset Library, Run History browser, Cost panel (Phase 2).
- Interactive charts + live streaming steps (Phase 3).
- Multi-file joins / Excel multi-sheet, column notes, clarify-vs-best-guess, deep
  refine (Phase 4).

## Tests

```
uv run pytest
```

Tests run against the **real Gemini key** from `.env` and the production SQLite
driver. The privacy, pipeline, API, and refine-loop tests under `tests/phase1/`
exercise the live agent end-to-end.
