from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from lead_gen_agent.config.settings import get_settings
from lead_gen_agent.db import repository as repo
from lead_gen_agent.db.session import create_db_session
from lead_gen_agent.domain.models import EU_COUNTRIES, SIZE_BANDS
from lead_gen_agent.graph.runner import run_pipeline

router = APIRouter()
_templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


def render(request: Request, name: str, **ctx):
    """Starlette ≥1.0 TemplateResponse signature. Always inject llm_provider banner context."""
    provider = get_settings().resolved_llm_provider
    ctx = {"llm_provider": provider, **ctx}
    return templates.TemplateResponse(request, name, ctx)


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/")
def home(request: Request):
    return render(
        request,
        "index.html",
        countries=EU_COUNTRIES,
        size_bands=SIZE_BANDS,
    )


@router.post("/runs")
def create_run(
    country: str = Form(...),
    industry: str = Form(...),
    size_band: str = Form(...),
):
    run_pipeline(country=country, industry=industry, size_band=size_band)
    return RedirectResponse(url="/runs", status_code=303)


@router.get("/runs")
def list_runs(request: Request):
    with create_db_session() as s:
        runs = repo.list_runs(s)
    return render(request, "runs.html", runs=runs)


@router.get("/leads")
def list_leads(
    request: Request,
    country: str | None = None,
    industry: str | None = None,
    size_band: str | None = None,
    min_score: int | None = None,
):
    with create_db_session() as s:
        leads = repo.list_leads(
            s, country=country or None, industry=industry or None,
            size_band=size_band or None, min_score=min_score,
        )
    return render(
        request,
        "leads.html",
        leads=leads,
        countries=EU_COUNTRIES,
        size_bands=SIZE_BANDS,
        filters={"country": country or "", "industry": industry or "", "size_band": size_band or "", "min_score": min_score or ""},
    )


@router.get("/leads.csv")
def leads_csv(
    country: str | None = None,
    industry: str | None = None,
    size_band: str | None = None,
    min_score: int | None = None,
):
    with create_db_session() as s:
        leads = repo.list_leads(
            s, country=country or None, industry=industry or None,
            size_band=size_band or None, min_score=min_score,
        )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["name", "website", "country", "industry", "size_band", "hq_city", "score", "rationale", "description"]
    )
    for l in leads:
        writer.writerow([
            l.name, l.website or "", l.country, l.industry, l.size_band,
            l.hq_city or "", l.score, l.rationale or "", l.description or "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="leads.csv"'},
    )
