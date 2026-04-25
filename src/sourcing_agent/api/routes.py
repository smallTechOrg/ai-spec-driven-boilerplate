"""All HTTP routes — web UI + JSON API."""

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from sourcing_agent.config.settings import get_settings
from sourcing_agent.db.repository import (
    create_run,
    get_run,
    get_run_with_details,
)
from sourcing_agent.db.session import get_session
from sourcing_agent.domain.models import MaterialRequest, SourcingRequest

router = APIRouter()

_templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


def _render(request: Request, name: str, **ctx):
    """Render a Jinja2 template using the Starlette ≥ 1.0 signature."""
    settings = get_settings()
    ctx["llm_provider"] = settings.resolved_llm_provider
    ctx["is_stub"] = ctx["llm_provider"] == "stub"
    return templates.TemplateResponse(request, name, ctx)


def _run_agent_background(run_id: uuid.UUID) -> None:
    from sourcing_agent.graph.runner import run_agent

    try:
        run_agent(run_id)
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Background agent run %s failed", run_id)


# ─── Health ──────────────────────────────────────────────────────────────────


@router.get("/health")
def health():
    return {"status": "ok"}


# ─── Web UI ───────────────────────────────────────────────────────────────────


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return _render(request, "index.html")


@router.post("/runs", response_class=HTMLResponse)
async def create_run_form(
    request: Request,
    background_tasks: BackgroundTasks,
):
    form = await request.form()
    errors: list[str] = []

    project_name = str(form.get("project_name", "")).strip()
    if not project_name:
        errors.append("Project name is required.")

    # Collect materials from form fields named material_name[], quantity[], unit[]
    names = form.getlist("material_name[]")
    quantities = form.getlist("quantity[]")
    units = form.getlist("unit[]")

    materials: list[MaterialRequest] = []
    for name, qty, unit in zip(names, quantities, units):
        name = name.strip()
        unit = unit.strip()
        if not name:
            continue
        try:
            quantity = float(qty)
            if quantity <= 0:
                raise ValueError("must be positive")
        except (ValueError, TypeError):
            errors.append(f"Invalid quantity for '{name}': must be a positive number.")
            continue
        materials.append(MaterialRequest(name=name, quantity=quantity, unit=unit))

    if not materials:
        errors.append("At least one material is required.")

    if errors:
        return _render(request, "index.html", errors=errors, project_name=project_name)

    with get_session() as session:
        run = create_run(session, project_name, materials)
        run_id = run.id

    background_tasks.add_task(_run_agent_background, run_id)
    return RedirectResponse(url=f"/runs/{run_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/runs/{run_id}", response_class=HTMLResponse)
def run_status_page(request: Request, run_id: uuid.UUID):
    with get_session() as session:
        run = get_run(session, run_id)
        if run is None:
            return _render(request, "error.html", message=f"Run {run_id} not found.")
        return _render(
            request,
            "status.html",
            run_id=str(run_id),
            project_name=run.project_name,
            run_status=run.status,
        )


@router.get("/runs/{run_id}/report", response_class=HTMLResponse)
def run_report_page(request: Request, run_id: uuid.UUID):
    with get_session() as session:
        run = get_run_with_details(session, run_id)
        if run is None:
            return _render(request, "error.html", message=f"Run {run_id} not found.")
        if run.status != "completed":
            return RedirectResponse(url=f"/runs/{run_id}", status_code=status.HTTP_302_FOUND)

        materials_data = []
        for item in run.line_items:
            recs = sorted(item.recommendations, key=lambda r: r.rank)
            recommendations = [
                {
                    "rank": r.rank,
                    "supplier_name": r.supplier_name,
                    "supplier_location": r.supplier_location or "—",
                    "price_per_unit": float(r.price_per_unit),
                    "currency": r.currency,
                    "lead_time_days": r.lead_time_days,
                    "certifications": r.certifications or "None",
                    "score": float(r.score),
                }
                for r in recs
            ]
            materials_data.append(
                {
                    "material_name": item.material_name,
                    "quantity": float(item.quantity),
                    "unit": item.unit,
                    "recommendations": recommendations,
                }
            )

        return _render(
            request,
            "report.html",
            run_id=str(run_id),
            project_name=run.project_name,
            completed_at=run.completed_at,
            materials=materials_data,
        )


# ─── JSON API ─────────────────────────────────────────────────────────────────


@router.post("/api/runs", status_code=status.HTTP_201_CREATED)
def api_create_run(body: SourcingRequest, background_tasks: BackgroundTasks):
    with get_session() as session:
        run = create_run(session, body.project_name, body.materials)
        run_id = run.id
    background_tasks.add_task(_run_agent_background, run_id)
    return {"run_id": str(run_id), "status": "pending"}


@router.get("/api/runs/{run_id}/status")
def api_run_status(run_id: uuid.UUID):
    with get_session() as session:
        run = get_run(session, run_id)
        if run is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        return {
            "run_id": str(run_id),
            "status": run.status,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }


@router.get("/api/runs/{run_id}/report")
def api_run_report(run_id: uuid.UUID):
    with get_session() as session:
        run = get_run_with_details(session, run_id)
        if run is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        if run.status != "completed":
            return JSONResponse({"error": "run not completed", "status": run.status}, status_code=409)

        materials_data = []
        for item in run.line_items:
            recs = sorted(item.recommendations, key=lambda r: r.rank)
            materials_data.append(
                {
                    "material_name": item.material_name,
                    "quantity": float(item.quantity),
                    "unit": item.unit,
                    "recommendations": [
                        {
                            "rank": r.rank,
                            "supplier_name": r.supplier_name,
                            "supplier_location": r.supplier_location,
                            "price_per_unit": float(r.price_per_unit),
                            "currency": r.currency,
                            "lead_time_days": r.lead_time_days,
                            "certifications": r.certifications,
                            "score": float(r.score),
                        }
                        for r in recs
                    ],
                }
            )

        return {
            "run_id": str(run_id),
            "project_name": run.project_name,
            "status": run.status,
            "materials": materials_data,
        }
