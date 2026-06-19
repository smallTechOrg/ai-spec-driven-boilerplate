# Pattern: Interface / serving (Layer 10)

How the agent reaches the outside world: an async FastAPI app exposing `/health`, `POST /runs`, and the
built-in `/traces` viewer. **Generate this fresh at build time**, pinning the *current* `fastapi` /
`uvicorn` (check the latest first — a guessed/old version 404s). The code below is proven working.

The graph and loop come from `patterns/react-agent.md`; the span emission feeding the viewer from
`patterns/observability-and-evals.md`; the runtime model from `patterns/model-and-providers.md`. This
recipe owns the serving edge **and** the self-contained `/traces` viewer (one runnable `server.py`).

## Contract
- `GET /health` → `{"ok": true}` — the liveness probe the demo gate hits.
- `POST /runs {"goal": "..."}` → runs the agent, returns the `ok()` envelope with the answer + run id.
- `GET /` → redirect to `/traces`; `GET /traces` → server-rendered timeline (no JS).
- Port **8001** (override `APP_PORT`). One envelope shape everywhere: `ok(data)` / `err(msg)`.

## Code — `agent/runner.py` (proven, verbatim)
Drives one run end-to-end: create the `Run`, build the graph, seed the domain system prompt + goal, invoke
under the `invoke_agent` span, persist messages + outcome. `run_id` is returned so the caller can deep-link
into `/traces`.
```python
import uuid
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy import select
from .config import get_settings
from .db import Message, Run, get_sessionmaker
from .graph import build_graph
from .llm import get_model
from .observability import span

DOMAIN_PROMPT = (  # the spec-writer overwrites this from spec/product.md (domain instructions)
    "You are a focused task agent. Use the tools available. Call finish when you have the answer."
)

async def run_agent(goal: str, model=None, run_id: str | None = None) -> dict:
    settings = get_settings()
    run_id = run_id or uuid.uuid4().hex
    model = model or get_model()

    async with get_sessionmaker()() as s:
        s.add(Run(id=run_id, goal=goal, status="running", iterations=0))
        await s.commit()

    graph = build_graph(model)
    state = {
        "messages": [SystemMessage(content=DOMAIN_PROMPT), HumanMessage(content=goal)],
        "iterations": 0, "answer": None, "run_id": run_id,
    }
    async with span(run_id, "invoke_agent", "INTERNAL", goal=goal):
        result = await graph.ainvoke(state, config={"recursion_limit": 50})

    async with get_sessionmaker()() as s:
        for m in result["messages"]:
            role = "assistant" if isinstance(m, AIMessage) else getattr(m, "type", "system")
            content = m.content if isinstance(m.content, str) else str(m.content)
            s.add(Message(id=uuid.uuid4().hex, run_id=run_id, role=role, content=content))
        run = (await s.execute(select(Run).where(Run.id == run_id))).scalar_one()
        run.status, run.answer, run.iterations = "completed", result["answer"], result["iterations"]
        await s.commit()

    return {"run_id": run_id, "answer": result["answer"],
            "iterations": result["iterations"], "messages": result["messages"]}
```

## Code — `agent/server.py` (proven, verbatim — self-contained, the `/traces` viewer lives here)
The whole serving edge in one runnable file: `app = FastAPI(lifespan=...)` plus `/health`, `POST /runs`,
and the inline `/traces` viewer (server-rendered HTML, no JS — `_traces_html` is the small helper). The
span emission feeding this viewer is owned by `patterns/observability-and-evals.md`; the rendering lives
here. `KIND_COLOR` maps the three span kinds the loop emits: `INTERNAL` (top run span), `LLM`, `TOOL`.
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from .db import get_sessionmaker, init_db, Run, Span
from .runner import run_agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()                          # create_all — sqlite local-first
    yield

app = FastAPI(title="agent", lifespan=lifespan)

def ok(data):  return {"ok": True, "data": data}
def err(msg):  return {"ok": False, "error": msg}

class RunIn(BaseModel):
    goal: str

@app.get("/health")
async def health():
    return ok({"status": "alive"})

@app.post("/runs")
async def create_run(body: RunIn):
    try:
        return ok(await run_agent(body.goal))   # run_agent returns a dict — serialized straight into ok()
    except Exception as e:                    # surface key/model failures as JSON, not a 500 stacktrace
        return err(str(e))

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/traces")

KIND_COLOR = {"INTERNAL": "#6b7280", "LLM": "#2563eb", "TOOL": "#16a34a"}

def _esc(x) -> str:
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

async def _traces_html() -> str:
    async with get_sessionmaker()() as s:
        runs = (await s.execute(select(Run).order_by(Run.created_at.desc()))).scalars().all()
        spans = (await s.execute(select(Span).order_by(Span.start_ms))).scalars().all()
    by_run: dict[str, list[Span]] = {}
    for sp in spans:
        by_run.setdefault(sp.run_id, []).append(sp)
    rows = []
    for r in runs:
        rspans = by_run.get(r.id, [])
        maxd = max((sp.duration_ms for sp in rspans), default=1) or 1
        rows.append(f"<h2>{_esc(r.goal)} <small>[{_esc(r.status)}] · {len(rspans)} spans</small></h2>")
        for sp in rspans:
            color = KIND_COLOR.get(sp.kind, "#6b7280")
            bar = max(2, int(200 * sp.duration_ms / maxd))
            err_attr = sp.attributes.get("error") if isinstance(sp.attributes, dict) else None
            err_html = f"<div style='color:#dc2626'>{_esc(err_attr)}</div>" if err_attr else ""
            rows.append(
                f"<div style='margin:4px 0'>"
                f"<span style='background:{color};color:#fff;padding:1px 6px;border-radius:4px'>{_esc(sp.kind)}</span> "
                f"<b>{_esc(sp.name)}</b> "
                f"<span style='display:inline-block;height:8px;width:{bar}px;background:{color};vertical-align:middle'></span> "
                f"{sp.duration_ms}ms"
                f"<pre style='margin:2px 0;color:#374151'>{_esc(sp.attributes)}</pre>{err_html}</div>"
            )
    body = "".join(rows) or "<p>No runs yet. POST a goal to /runs.</p>"
    return f"<html><body style='font-family:system-ui;max-width:900px;margin:2rem auto'><h1>Traces</h1>{body}</body></html>"

@app.get("/traces", response_class=HTMLResponse)
async def traces():
    return await _traces_html()              # server-rendered HTML, no JS
```

## Code — `agent/__main__.py` (proven, verbatim)
```python
import uvicorn
from .config import get_settings

if __name__ == "__main__":
    s = get_settings()
    uvicorn.run("agent.server:app", host="0.0.0.0", port=s.port, reload=False)
```
Run it: `python -m agent` → `http://localhost:8001`. `GET /health` is the demo gate's liveness check;
the deploy artifact serves the same app (`patterns/durability.md`, deploy ladder).

## SSE token streaming (sketch — add when the UI wants live tokens)
`POST /runs` returns the whole answer; for a typing-cursor UX stream tokens over **Server-Sent Events**.
Stream from `graph.astream_events` (LangGraph emits `on_chat_model_stream` chunks) and forward each token
as an SSE `data:` line. One extra endpoint, no protocol change to the rest:
```python
import json
from fastapi.responses import StreamingResponse

@app.post("/runs/stream")
async def stream_run(body: RunIn):
    async def gen():
        async for ev in stream_agent(body.goal):        # wraps graph.astream_events(..., version="v2")
            if ev["event"] == "on_chat_model_stream" and (tok := ev["data"]["chunk"].content):
                yield f"data: {json.dumps({'token': tok})}\n\n"
            elif ev["event"] == "on_chain_end" and ev["name"] == "finalize":
                yield f"data: {json.dumps({'done': True, 'answer': ev['data']['output']['answer']})}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")
```
Headers that bite in prod: `Cache-Control: no-cache`, `X-Accel-Buffering: no` (disable proxy buffering).
Client reads with `EventSource` / `fetchEventSource`. The span wrapping is unchanged — streaming is a view
over the same run, still persisted and visible in `/traces`.

## UI — Next.js + React + Tailwind, primary journey only
The harness builds a UI **by default**; **headless products skip it** (set in `spec/tech-stack.md` — an
API/cron/Slack-only agent ships no web UI). When built, scope it to the **primary journey** the user
described in `spec/product.md` — *not* a screen per capability. Usually one page: enter a goal → see the
answer stream in → a link to its trace. The agent's value is the run, not the chrome.

- **Stack:** Next.js (App Router) + React + Tailwind. The page calls `POST /runs` (or `/runs/stream` for
  SSE) and renders the `ok()` envelope. Keep state minimal — input, streaming answer, run-id link.
- **Always render the answer as markdown.** LLM output *is* markdown — headings, tables, lists, code,
  bold. Render it through a markdown component (`react-markdown` + `remark-gfm` for tables/strikethrough),
  never as raw text or `{answer}` in a `<pre>`. Stream tokens into that same markdown surface so the
  formatted answer builds up live. A wall of unformatted text is a bug, not a style choice.
- **Honesty:** real network call to the real agent. No mocked answer, no fake latency, no lorem.
- **Deep-link the trace:** show `run_id` as a link to `/traces` so a human can inspect the actual steps —
  the UI and the observability layer are the same truth (`patterns/observability-and-evals.md`).
- **Don't rebuild `/traces`.** The server already renders the timeline; the UI links to it.
- **One command runs both.** Ship a `make dev` that starts backend **and** UI together
  (`trap 'kill 0' INT; python -m agent & cd ui && npm run dev`) — Ctrl-C kills both. The user never starts the
  backend by hand; a UI with a dead backend is the most common "it's broken" report.
- **Persist the session client-side.** For multi-turn UIs, store `thread_id` (and the active resource id) in
  `localStorage` so a page reload resumes the same conversation — React state alone resets to a fresh thread
  on every refresh, which reads to the user as "all my history vanished."
- **Show cost where the user works.** Surface per-run tokens + cost in the product UI, not only at `/traces`,
  and keep a running session total visible. Cost you can't see is cost you discover too late.

### Visualizations — suggest minimal, let the user drive (data / analytics products only)
Skip this entirely for non-data products. When the product *does* produce charts, do **not** auto-render a
wall of dashboards the user never asked for — that pre-judges what matters and buries the answer in noise.
Charts are an **affordance, not the default surface**: the primary journey stays ask → answer, and
visualization is opt-in and user-driven.
- **Suggest, don't flood.** Offer a few sensible default charts inferred from the schema (one per key
  column or relationship) as one-click suggestions — not a pre-built board of everything.
- **User-authored charts.** The user adds a chart by typing a natural-language prompt ("revenue by region
  as a bar chart"); the agent returns the chart spec (Plotly JSON via the `finish` tool —
  `patterns/react-agent.md`) and the UI renders it. The chart comes from a real run, not a hardcoded view.
- **Fine-tune by prompt.** Each chart keeps its prompt editable — the user refines the wording and the
  chart regenerates. A chart is a conversation, not a frozen artifact.

### Gate — Playwright asserts the post-JS DOM (run it, don't trust it)
The journey test drives a real browser against the running app and asserts what a user actually sees
*after* React hydrates and the answer arrives — never the raw HTML, never a 200 alone. → `workflows/gates.md`.
```python
# tests/e2e/test_primary_journey.py  (pytest + playwright; agent server + next dev both up)
from playwright.sync_api import expect

def test_user_gets_an_answer(page):
    page.goto("http://localhost:3000")
    page.get_by_role("textbox", name="goal").fill("What does the onboarding doc say about refunds?")
    page.get_by_role("button", name="Run").click()
    answer = page.get_by_test_id("answer")
    expect(answer).not_to_be_empty(timeout=30_000)        # post-JS DOM, after the real run completes
    expect(page.get_by_role("link", name="trace")).to_be_visible()   # deep-link to /traces present
```
A headless product replaces this with the API + outcome-eval gate only (no browser). The mechanical
two-tier success (demo / productionise) is defined in `harness/harness.md` and `workflows/gates.md` — this
recipe just wires the serving edge into it.
