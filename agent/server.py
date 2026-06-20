from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

from .config import validate_required_config
from .db import Run, Span, get_sessionmaker, init_db
from .runner import run_agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_required_config()               # fail LOUD at boot if required config is missing (config.py)
    await init_db()                          # create_all — sqlite local-first
    # SHORT-TERM (multi-turn) MEMORY: open ONE AsyncSqliteSaver for the process and keep it on app state, so
    # follow-up turns on the same session_id resume the thread. This is what makes the two-turn gate's Q2
    # see Q1's context (workflows/gates.md check 5).
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver   # pip: langgraph-checkpoint-sqlite
    cm = AsyncSqliteSaver.from_conn_string("checkpoints.db")
    app.state.checkpointer = await cm.__aenter__()
    try:
        yield
    finally:
        await cm.__aexit__(None, None, None)


app = FastAPI(title="support-triage-agent", lifespan=lifespan)


# One envelope shape EVERYWHERE: ok(data) on success, api_error(code, ...) on failure — never an error page.
def ok(data):
    return {"ok": True, "data": data}


class ApiError(Exception):
    def __init__(self, code: str, msg: str = "", status: int = 500):
        self.code, self.msg, self.status = code, msg or code, status


def api_error(code: str, msg: str = "", status: int = 500) -> ApiError:
    return ApiError(code, msg, status)


@app.exception_handler(ApiError)
async def _api_error_handler(_req, exc: ApiError):
    from fastapi.responses import JSONResponse
    return JSONResponse({"ok": False, "error": {"code": exc.code, "message": exc.msg}}, status_code=exc.status)


class RunIn(BaseModel):
    goal: str
    session_id: str | None = None        # optional — ties follow-up turns to one session/thread (two-turn gate)


@app.get("/health")
async def health():
    return ok({"status": "alive"})


@app.post("/runs")
async def create_run(request: Request, body: RunIn):
    try:
        # READ the checkpointer with getattr, NOT a bare attribute — httpx's ASGITransport (the keyless
        # contract test) does NOT run the lifespan, so app.state.checkpointer is unset there.
        checkpointer = getattr(request.app.state, "checkpointer", None)
        return ok(await run_agent(body.goal, session_id=body.session_id, checkpointer=checkpointer))
    except ApiError:
        raise
    except Exception as e:                        # surface key/model failures as a CODED JSON error
        raise api_error("RUN_FAILED", str(e), status=500)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/traces")


KIND_COLOR = {"INTERNAL": "#6b7280", "LLM": "#2563eb", "TOOL": "#16a34a"}
KIND_PLAIN = {"INTERNAL": "Run step", "LLM": "Asked the AI model", "TOOL": "Used a tool"}


def _esc(x) -> str:
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _plain_step(sp) -> str:
    """Turn a span name into a human sentence. `execute_tool.classify_ticket` -> 'Used a tool: classify ticket'."""
    if sp.name.startswith("execute_tool."):
        return "Used a tool: " + sp.name.removeprefix("execute_tool.").replace("_", " ")
    if sp.kind == "LLM":
        return "Asked the AI model"
    if sp.name == "invoke_agent":
        return "Ran the agent"
    return KIND_PLAIN.get(sp.kind, sp.name)


async def _traces_html() -> str:
    async with get_sessionmaker()() as s:
        runs = (await s.execute(select(Run).order_by(Run.created_at.desc()))).scalars().all()
        spans = (await s.execute(select(Span).order_by(Span.start_ms))).scalars().all()
    by_run: dict[str, list[Span]] = {}
    for sp in spans:
        by_run.setdefault(sp.run_id, []).append(sp)

    # --- OVERVIEW BAND: the at-a-glance numbers a non-technical reader wants first --------------------
    total = len(runs)
    ok_runs = sum(1 for r in runs if r.status == "completed")
    total_cost = sum(r.cost_usd or 0 for r in runs)
    total_tokens = sum((r.input_tokens or 0) + (r.output_tokens or 0) for r in runs)

    def _run_ms(rid):
        sp = by_run.get(rid) or []
        return max((s.end_ms - s.start_ms for s in sp), default=0)

    avg_ms = (sum(_run_ms(r.id) for r in runs) / total) if total else 0

    def _card(label, value):
        return (f"<div style='flex:1;min-width:120px;background:#f9fafb;border:1px solid #e5e7eb;"
                f"border-radius:8px;padding:12px'><div style='font-size:22px;font-weight:700'>{value}</div>"
                f"<div style='color:#6b7280;font-size:13px'>{_esc(label)}</div></div>")

    overview = (
        "<div style='display:flex;gap:12px;flex-wrap:wrap;margin:0 0 24px'>"
        + _card("runs", total)
        + _card("succeeded", f"{ok_runs}/{total}" + (f" ({100*ok_runs//total}%)" if total else ""))
        + _card("total cost", f"${total_cost:.4f}")
        + _card("avg cost / run", f"${(total_cost/total if total else 0):.4f}")
        + _card("total tokens", f"{total_tokens:,}")
        + _card("avg answer time", f"{avg_ms/1000:.1f}s")
        + "</div>"
    )

    # --- DRILL-DOWN: one collapsible card per run, each step narrated in plain English ----------------
    rows = []
    for r in runs:
        rspans = by_run.get(r.id, [])
        maxd = max((sp.duration_ms for sp in rspans), default=1) or 1
        badge = "#16a34a" if r.status == "completed" else "#dc2626" if r.status == "error" else "#d97706"
        meta = (f"<span style='color:{badge};font-weight:600'>{_esc(r.status)}</span> · "
                f"{len(rspans)} steps · ${r.cost_usd or 0:.4f} · "
                f"{(r.input_tokens or 0)+(r.output_tokens or 0):,} tokens")
        steps = []
        for sp in rspans:
            color = KIND_COLOR.get(sp.kind, "#6b7280")
            bar = max(2, int(200 * sp.duration_ms / maxd))
            err_attr = sp.attributes.get("error") if isinstance(sp.attributes, dict) else None
            err_html = f"<div style='color:#dc2626;margin-left:8px'>⚠ {_esc(err_attr)}</div>" if err_attr else ""
            steps.append(
                f"<div style='margin:4px 0'>"
                f"<b>{_esc(_plain_step(sp))}</b> "
                f"<span style='display:inline-block;height:8px;width:{bar}px;background:{color};vertical-align:middle'></span> "
                f"<span style='color:#6b7280'>{sp.duration_ms/1000:.2f}s</span> "
                f"<span style='color:#9ca3af;font-size:12px'>{_esc(sp.name)}</span>"
                f"<pre style='margin:2px 0 2px 8px;color:#374151;font-size:12px;white-space:pre-wrap'>{_esc(sp.attributes)}</pre>"
                f"{err_html}</div>"
            )
        # The run_id MUST appear VERBATIM in the rendered HTML — gate check 8 greps it.
        rows.append(
            f"<details id='{_esc(r.id)}' style='border:1px solid #e5e7eb;border-radius:8px;padding:12px;margin:0 0 12px'{' open' if r is runs[0] else ''}>"
            f"<summary style='cursor:pointer'><b>{_esc(r.goal)}</b> "
            f"<span style='color:#9ca3af;font-size:12px;font-weight:400'>{_esc(r.id)}</span>"
            f"<br><small>{meta}</small></summary>"
            f"<div style='margin-top:8px'>{''.join(steps) or '<i>no steps recorded</i>'}</div></details>"
        )
    body = overview + ("".join(rows) or "<p>No runs yet. POST a goal to /runs.</p>")
    return (f"<html><body style='font-family:system-ui;max-width:900px;margin:2rem auto'>"
            f"<h1>Observability dashboard</h1>"
            f"<p style='color:#6b7280'>Every run the agent did, in plain English — what it did, whether it worked, what it cost.</p>"
            f"{body}</body></html>")


@app.get("/traces", response_class=HTMLResponse)
async def traces():
    return await _traces_html()              # server-rendered HTML, no JS
