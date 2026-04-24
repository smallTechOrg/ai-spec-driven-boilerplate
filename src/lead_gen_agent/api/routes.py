"""All HTTP routes."""
from __future__ import annotations

import asyncio
import csv
import io
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

import os

from lead_gen_agent.config import get_settings
from lead_gen_agent.db import create_db_session
from lead_gen_agent.db.repository import LeadRepository, SearchRunRepository
from lead_gen_agent.domain import SearchCriteria, SearchRunCreate
from lead_gen_agent.graph.progress import get_queue, register_run
from lead_gen_agent.graph.runner import run_agent

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)

router = APIRouter()


def render(request: Request, name: str, **ctx) -> HTMLResponse:
    """Render a Jinja2 template. Injects llm_provider for stub-mode banner."""
    ctx["llm_provider"] = get_settings().resolved_llm_provider
    ctx["request"] = request
    return templates.TemplateResponse(request, name, ctx)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@router.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    country: str = "",
    industry: str = "",
    status: str = "",
):
    with create_db_session() as session:
        lead_repo = LeadRepository(session)
        run_repo = SearchRunRepository(session)
        leads = lead_repo.list_leads(
            country=country or None,
            industry=industry or None,
            status=status or None,
        )
        runs = run_repo.list_all()

    return render(
        request,
        "dashboard.html",
        leads=leads,
        runs=runs,
        filters={"country": country, "industry": industry, "status": status},
    )


# ---------------------------------------------------------------------------
# New search form
# ---------------------------------------------------------------------------

@router.get("/runs/new", response_class=HTMLResponse)
def new_run_form(request: Request):
    return render(request, "new_run.html")


@router.post("/runs")
async def create_run(
    request: Request,
    country: Annotated[str, Form()],
    industry: Annotated[str, Form()],
    size_min: Annotated[str, Form()] = "",
    size_max: Annotated[str, Form()] = "",
):
    size_min_int = int(size_min) if size_min.strip() else None
    size_max_int = int(size_max) if size_max.strip() else None

    # Create the run record first
    with create_db_session() as session:
        run_repo = SearchRunRepository(session)
        run = run_repo.create(SearchRunCreate(
            country=country,
            industry=industry,
            size_min=size_min_int,
            size_max=size_max_int,
        ))
        run_id = run.id

    # Register progress queue before spawning background task so that the
    # SSE endpoint can connect immediately after the redirect.
    register_run(run_id)

    criteria = SearchCriteria(
        country=country,
        industry=industry,
        size_min=size_min_int,
        size_max=size_max_int,
    )

    # Run pipeline in a thread so it doesn't block the event loop.
    asyncio.create_task(asyncio.to_thread(run_agent, run_id, criteria))

    return RedirectResponse(url=f"/runs/{run_id}", status_code=303)


# ---------------------------------------------------------------------------
# Run results
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}", response_class=HTMLResponse)
def run_results(request: Request, run_id: str):
    with create_db_session() as session:
        run_repo = SearchRunRepository(session)
        lead_repo = LeadRepository(session)
        run = run_repo.get(run_id)
        leads = lead_repo.list_by_run(run_id) if run else []

    if not run:
        return render(request, "404.html", message=f"Run {run_id} not found")

    return render(request, "run_results.html", run=run, leads=leads)


# ---------------------------------------------------------------------------
# SSE — live progress stream for a running pipeline
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}/events")
async def run_events(run_id: str):
    """Server-Sent Events stream for live pipeline progress."""

    async def generate():
        q = get_queue(run_id)
        if q is None:
            # Run already finished or unknown — send done immediately
            yield "event: done\ndata: {}\n\n"
            return
        while True:
            msg = await q.get()
            if msg is None:  # sentinel — pipeline finished
                yield "event: done\ndata: {}\n\n"
                break
            yield f"data: {json.dumps(msg)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

@router.get("/leads/export.csv")
def export_csv(
    country: str = "",
    industry: str = "",
    status: str = "",
):
    with create_db_session() as session:
        leads = LeadRepository(session).list_leads(
            country=country or None,
            industry=industry or None,
            status=status or None,
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "company_name", "domain", "website", "country",
        "industry", "headcount_estimate", "why_fit",
        "contact_name", "contact_title", "contact_email", "contact_phone",
        "status", "created_at",
    ])
    for lead in leads:
        # Flatten first contact into CSV columns; remaining contacts omitted
        first = lead.contacts[0] if lead.contacts else None
        writer.writerow([
            lead.company_name, lead.domain, lead.website, lead.country,
            lead.industry, lead.headcount_estimate, lead.why_fit,
            first.name if first else "",
            first.title if first else "",
            first.email if first else "",
            first.phone if first else "",
            lead.status, lead.created_at.isoformat() if lead.created_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )

