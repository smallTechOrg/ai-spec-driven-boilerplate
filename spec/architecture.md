# Architecture

## System Overview

A single-origin web application. One FastAPI process serves both the JSON API and the
pre-built Next.js static export (`frontend/out` mounted at `/app`). The agent core is a
LangGraph graph that orchestrates a **local-compute / LLM-plan** loop: the LLM decides *what
to compute* from schema + a bounded sample, and a **local sandboxed pandas step** does the
actual computation over the full local dataframe. Persistence is SQLite via SQLAlchemy +
Alembic. The LLM provider is Gemini, auto-detected from the configured key.

```
Browser (Next.js static export at /app)
        │  HTTP (same origin :8001)
        ▼
FastAPI  ── /datasets (upload)            ── stores file locally, derives schema+sample
         ── /datasets/{id}/ask (query)    ── invokes the agent runner
         ── /health
        │
        ▼
graph.runner.run_query ──> LangGraph graph (spec/agent.md)
        │                         │
        │     ┌───────────────────┼─────────────────────────────┐
        │     ▼                   ▼                              ▼
        │  load_dataset      propose_code (LLM: schema+sample)  execute_code (LOCAL sandbox)
        │  (local pandas)    explain_result (LLM: numbers only) finalize/handle_error
        ▼
SQLite (datasets + queries, incl. captured code)
        ▲
Local filesystem (data/uploads/<dataset_id>.<ext>)  ← FULL RAW DATA NEVER LEAVES THE BOX
```

## Core Design Guarantees

### Data stays local

- The uploaded file is written to `data/uploads/<dataset_id>.<ext>` on the local filesystem.
- On each query the file is loaded into a pandas DataFrame **locally**.
- The **only** dataset-derived content sent to the LLM is:
  - the **schema** (column names + inferred dtypes), and
  - a **bounded sample/summary**: the first N rows (default 20) plus per-column summary stats
    (count, null count, min/max/mean for numerics, top categories for objects).
- The **full DataFrame is never serialized to the LLM**. The LLM proposes code from
  schema+sample; the sandbox runs that code over the full local DataFrame.
- The observability log records, per query, the byte size and row count of what was sent to
  the LLM, so the "schema+sample only" guarantee is auditable.

### Show its work

- The exact code string the LLM proposed and the agent executed is captured into the
  `QueryRow.code` column and returned in the `/ask` response.
- The numeric result of executing that code is captured into `QueryRow.result_json`.
- The plain-language explanation is captured into `QueryRow.explanation`.
- Answer + explanation + code are returned together on every query and rendered in the UI.

### Local code sandbox

LLM-proposed code is executed in a **restricted local Python environment**, never `eval` of
arbitrary code reached over the network:

- Execution runs `exec` of the proposed code in a **constrained namespace** that exposes only
  `df` (the DataFrame), `pd` (pandas), and a small allow-list of builtins; `__import__`,
  filesystem, network, and `os`/`subprocess` access are removed from the namespace.
- The contract: the proposed code must assign its answer to a variable named `result`. The
  sandbox returns `result` (coerced to a JSON-serializable form) or a structured error.
- A **wall-clock timeout** (default 10 s) bounds execution; on timeout or any exception the
  sandbox returns a structured `{error, traceback_summary}` that the graph turns into a repair
  attempt or a human-readable failure.

> **Assumed:** The sandbox is an **in-process restricted-namespace `exec`** with a thread-based
> wall-clock timeout and a stripped builtins/globals dict — chosen because the threat model is
> *the agent's own LLM-proposed code*, not adversarial user code (uploads are the user's own
> data on the user's own machine). It is NOT a full OS-level container/jail. This is the
> right-sized v1 control; a stronger isolation layer (subprocess + seccomp / container) is a
> future hardening, not a v1 requirement.

> **Assumed:** One **code-repair retry**. If the first proposed code errors in the sandbox, the
> graph feeds the error back to the LLM once for a corrected version (bounded by the existing
> `react_max_steps` budget). A second failure → graceful human-readable error.

## Components

| Component | Path | Responsibility |
|-----------|------|----------------|
| Settings | `src/config/settings.py` | pydantic-settings, `env_prefix=AGENT_`; provider auto-detect; adds analysis caps (sample rows, sandbox timeout, upload size) |
| LLM client + providers | `src/llm/` | Provider-agnostic call surface; Gemini provider active |
| Model router | `src/llm/router.py` | Logical task → concrete model id (blank → provider default `gemini-2.5-flash`) |
| Dataset tool | `src/tools/dataset.py` | Local CSV(/Excel) load → DataFrame; derive schema + bounded sample/summary |
| Sandbox tool | `src/tools/sandbox.py` | Execute LLM-proposed pandas code locally over the full DataFrame, with timeout + restricted namespace; capture result or structured error |
| Agent graph | `src/graph/` | LangGraph nodes/edges/state/runner for the analysis loop (see `spec/agent.md`) |
| Prompts | `src/prompts/transform.md` | Replaced with the analysis system prompt (code-proposal + explanation) |
| DB models + session | `src/db/` | `DatasetRow`, `QueryRow` (+ existing `RunRow`/`TurnRow`); SQLAlchemy + Alembic |
| API | `src/api/` | `/datasets` (upload), `/datasets/{id}/ask`, `/health`; mounts `frontend/out` at `/app` |
| Domain models | `src/domain/` | Request/response pydantic models for upload + ask |
| Observability | `src/observability/events.py` | structlog structured logging per operation |
| Frontend | `frontend/src/app/page.tsx` | Upload + question + answer(numbers/explanation/code) UI + labelled stubs; static export |

## Data Flow (one query, Phase 1)

1. **Upload** — `POST /datasets` (multipart). File saved to `data/uploads/<id>.csv`; the file
   is loaded once to validate it parses and to derive + persist schema + sample/summary onto
   `DatasetRow`. Response: `{dataset_id, schema, row_count, sample_preview}`.
2. **Ask** — `POST /datasets/{id}/ask` with `{question}` → `graph.runner.run_query`.
3. **load_dataset** (local) — load `data/uploads/<id>.csv` into `df`; attach schema+sample to
   state. No LLM.
4. **propose_code** (LLM) — send system prompt + schema + sample + question → Gemini returns a
   pandas snippet assigning to `result`. Full data NOT sent.
5. **execute_code** (local sandbox) — run the snippet over the full `df`; capture `result` or a
   structured error. On error → one repair loop back to `propose_code`.
6. **explain_result** (LLM) — send the question + the captured numeric `result` (numbers only,
   not the dataset) → Gemini returns a short plain-language explanation.
7. **finalize** — persist `QueryRow{question, code, result_json, explanation, tokens, cost,
   latency, model}`; return `{answer, explanation, code, result}`.

## Stack

- **Language:** Python 3.12+ (backend), TypeScript/React (frontend).
- **Agent framework:** LangGraph (multi-step, conditional flow with a local-execution node and
  a repair loop). The full graph is specified in `spec/agent.md`.
- **LLM provider:** Google **Gemini**, auto-detected from `AGENT_GEMINI_API_KEY` (already set
  in `.env`). Default model **`gemini-2.5-flash`** (blank `llm_model`/router → provider
  default). Model routing tiers via `AGENT_MODEL_*` (kept env-configurable; not required for
  v1).
- **Backend:** FastAPI (single process, single origin). Entry point `python -m src` on port
  **8001**.
- **Database:** **SQLite** at `sqlite:///./data/agent.db` via SQLAlchemy + Alembic. **SQLite is
  the production driver for this project** — gate tests run against SQLite because it *is*
  production here. (Not PostgreSQL; qa-auditor must not flag a Postgres expectation.)
- **Frontend:** Next.js 15 + React 19, **static export** (`next build` → `frontend/out`),
  served single-origin by FastAPI at `/app`. Tailwind for styling.
- **Data libraries:** **pandas** (load + compute), **openpyxl** (Excel, Phase 3 only).
- **Key libraries:** pydantic / pydantic-settings, structlog, langgraph, google-genai (Gemini),
  pandas.
- **Dependency management:** **uv** (Python), **pnpm** (frontend).
- **Testing:** pytest (`uv run pytest`), `tests/unit` + `tests/integration` + e2e; real Gemini
  key from `.env`; real SQLite as the production driver.

## Assumptions

> **Assumed:** Upload limit — CSV up to **50 MB / 1,000,000 rows**; larger uploads are rejected
> with a clear error. Sample sent to the LLM is the first **20 rows** + per-column summary
> stats; configurable via `AGENT_SAMPLE_ROWS`.

> **Assumed:** Sandbox timeout default **10 s** (`AGENT_SANDBOX_TIMEOUT_S`); proposed code must
> assign to `result`; the namespace exposes only `df`, `pd`, and safe builtins.

> **Assumed:** Uploaded files persist on local disk under `data/uploads/`. No automatic
> deletion in v1 (single-user local tool); cleanup/retention is out of scope.

> **Assumed:** New settings fields added to `src/config/settings.py`: `sample_rows: int = 20`,
> `sandbox_timeout_s: float = 10.0`, `max_upload_mb: int = 50`, `max_rows: int = 1_000_000` —
> all `AGENT_`-prefixed and overridable from `.env`.

> **Assumed:** The existing `transform_text` capability slot and `RunRow`/`/runs` surface are
> superseded by the analysis capability; `transform_text` is removed from the composed graph
> path (the analysis nodes replace it). The generic ReAct seam nodes (`guard_input`,
> `load_memory`, `guard_output`, `write_memory`, `handle_error`, `finalize`) are reused where
> useful; `react` is replaced by the analysis nodes.
