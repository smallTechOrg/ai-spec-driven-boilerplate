"""Audit history endpoints — GET /api/runs and GET /api/runs/{run_id}."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api._common import api_error, ok
from db.models import RunRow
from db.session import get_session
from domain.ask import RunDetail, RunListItem, RunListResponse

router = APIRouter()


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


@router.get("/api/runs")
def list_runs(session: Session = Depends(get_session)) -> dict:
    rows = session.query(RunRow).order_by(RunRow.created_at.desc()).all()
    items = [
        RunListItem(
            id=r.id,
            dataset_id=r.dataset_id,
            status=r.status,
            question=r.question,
            generated_sql=r.generated_sql,
            est_usd=r.est_usd,
            created_at=_iso(r.created_at),
        )
        for r in rows
    ]
    return ok(RunListResponse(runs=items).model_dump())


@router.get("/api/runs/{run_id}")
def get_run(run_id: str, session: Session = Depends(get_session)) -> dict:
    run = session.get(RunRow, run_id)
    if run is None:
        raise api_error("NOT_FOUND", f"Run {run_id} not found", 404)

    plan_steps = json.loads(run.plan_json) if run.plan_json else []
    result_summary = json.loads(run.result_summary_json) if run.result_summary_json else None

    detail = RunDetail(
        id=run.id,
        dataset_id=run.dataset_id,
        status=run.status,
        question=run.question,
        plan_steps=plan_steps,
        generated_sql=run.generated_sql,
        result_summary=result_summary,
        prompt_tokens=run.prompt_tokens,
        completion_tokens=run.completion_tokens,
        est_usd=run.est_usd,
        error=run.error_message,
        created_at=_iso(run.created_at),
        updated_at=_iso(run.updated_at),
    )
    return ok(detail.model_dump())
