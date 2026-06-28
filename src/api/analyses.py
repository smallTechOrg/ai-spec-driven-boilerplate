"""Analyze + run-history endpoints. Response shapes per spec/api.md (raw JSON)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from api._common import api_error
from db.session import get_session
from db.models import Analysis
from graph.runner import run_analysis

router = APIRouter()


class AnalyzeRequest(BaseModel):
    dataset_id: str
    question: str


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _full(row: Analysis) -> dict:
    return {
        "id": row.id,
        "dataset_id": row.dataset_id,
        "question": row.question,
        "status": row.status,
        "answer": row.answer,
        "result": row.result,
        "chart_spec": row.chart_spec,
        "code": row.code,
        "steps_taken": row.steps_taken,
        "error_message": row.error_message,
        "created_at": _iso(row.created_at),
    }


@router.post("/api/analyses")
def create_analysis(
    req: AnalyzeRequest, session: Session = Depends(get_session)
) -> dict:
    if not req.question or not req.question.strip():
        raise api_error("BAD_REQUEST", "Question must not be empty.", 400)

    try:
        run_id = run_analysis(req.dataset_id, req.question.strip())
    except ValueError:
        raise api_error("NOT_FOUND", f"Unknown dataset_id: {req.dataset_id}", 404)
    except Exception as exc:
        raise api_error("INTERNAL", f"Analysis failed: {exc}", 500)

    row = session.get(Analysis, run_id)
    if row is None:
        raise api_error("INTERNAL", "Analysis row not found after run.", 500)
    return _full(row)


@router.get("/api/analyses")
def list_analyses(
    dataset_id: str = Query(...), session: Session = Depends(get_session)
) -> list[dict]:
    rows = session.scalars(
        select(Analysis)
        .where(Analysis.dataset_id == dataset_id)
        .order_by(Analysis.created_at.desc())
    ).all()
    return [
        {
            "id": r.id,
            "question": r.question,
            "status": r.status,
            "answer": r.answer,
            "code": r.code,
            "steps_taken": r.steps_taken,
            "created_at": _iso(r.created_at),
        }
        for r in rows
    ]


@router.get("/api/analyses/{analysis_id}")
def get_analysis(
    analysis_id: str, session: Session = Depends(get_session)
) -> dict:
    row = session.get(Analysis, analysis_id)
    if row is None:
        raise api_error("NOT_FOUND", f"Analysis {analysis_id} not found.", 404)
    return _full(row)
