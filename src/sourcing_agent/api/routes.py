from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select

from sourcing_agent.config.settings import get_settings
from sourcing_agent.db.models import (
    RecommendationRow,
    RunRow,
    SourcingRequestRow,
    SupplierRow,
)
from sourcing_agent.db.session import create_db_session
from sourcing_agent.graph.runner import run_agent

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

router = APIRouter()


def _ctx(request: Request, **extra) -> dict:
    s = get_settings()
    return {
        "request": request,
        "llm_provider": s.resolved_llm_provider,
        "search_provider": s.resolved_search_provider,
        **extra,
    }


def render(request: Request, name: str, **extra) -> HTMLResponse:
    return templates.TemplateResponse(request, name, _ctx(request, **extra))


@router.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@router.get("/", response_class=HTMLResponse)
def new_request(request: Request) -> HTMLResponse:
    return render(request, "form.html")


@router.post("/requests")
def submit_request(
    request: Request,
    material: str = Form(...),
    quantity: str = Form(...),
    location: str = Form(...),
    budget: str = Form(""),
    timeline: str = Form(""),
    criteria: str = Form(""),
):
    if not material.strip() or not quantity.strip() or not location.strip():
        raise HTTPException(status_code=400, detail="material, quantity, location are required")

    with create_db_session() as session:
        req = SourcingRequestRow(
            material=material.strip(),
            quantity=quantity.strip(),
            location=location.strip(),
            budget=budget.strip() or None,
            timeline=timeline.strip() or None,
            criteria=criteria.strip() or None,
        )
        session.add(req)
        session.flush()
        request_id = req.id

    run_id = run_agent(request_id)
    return RedirectResponse(url=f"/runs/{run_id}", status_code=303)


@router.get("/runs/{run_id}", response_class=HTMLResponse)
def run_report(request: Request, run_id: str) -> HTMLResponse:
    with create_db_session() as session:
        run = session.get(RunRow, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        req = session.get(SourcingRequestRow, run.request_id)

        rec_rows = session.execute(
            select(RecommendationRow)
            .where(RecommendationRow.run_id == run_id)
            .order_by(RecommendationRow.rank)
        ).scalars().all()

        sup_by_id = {
            s.id: s
            for s in session.execute(
                select(SupplierRow).where(SupplierRow.run_id == run_id)
            ).scalars().all()
        }

        recommendations = []
        for r in rec_rows:
            sup = sup_by_id.get(r.supplier_id)
            recommendations.append(
                {
                    "rank": r.rank,
                    "score": r.score,
                    "rationale": r.rationale,
                    "supplier": {
                        "name": sup.name if sup else "Unknown",
                        "location": sup.location if sup else None,
                        "price_indication": sup.price_indication if sup else None,
                        "lead_time": sup.lead_time if sup else None,
                        "source_url": sup.source_url if sup else None,
                        "notes": sup.notes if sup else None,
                    },
                }
            )

        run_view = {
            "id": run.id,
            "status": run.status,
            "error_message": run.error_message,
            "llm_provider": run.llm_provider,
            "search_provider": run.search_provider,
            "request": {
                "material": req.material,
                "quantity": req.quantity,
                "location": req.location,
                "budget": req.budget,
                "timeline": req.timeline,
                "criteria": req.criteria,
            },
            "recommendations": recommendations,
        }
    return render(request, "report.html", run=run_view)


@router.get("/runs", response_class=HTMLResponse)
def list_runs(request: Request) -> HTMLResponse:
    with create_db_session() as session:
        rows = session.execute(
            select(RunRow, SourcingRequestRow)
            .join(SourcingRequestRow, RunRow.request_id == SourcingRequestRow.id)
            .order_by(desc(RunRow.created_at))
            .limit(50)
        ).all()
        runs = [
            {
                "id": r.id,
                "status": r.status,
                "created_at": r.created_at,
                "material": req.material,
                "location": req.location,
            }
            for (r, req) in rows
        ]
    return render(request, "runs.html", runs=runs)
