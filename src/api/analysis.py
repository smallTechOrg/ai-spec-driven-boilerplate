"""Analysis API router — POST /api/analysis/run and GET /api/analysis/runs."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from api._common import ok
from db.session import get_session
from db.models import AnalysisRun, UploadedFile
from graph.runner import run_agent

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class RunRequest(BaseModel):
    file_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None


@router.post("/run")
def run_analysis(req: RunRequest, session: Session = Depends(get_session)) -> dict:
    """Invoke the LangGraph agent and return the analysis result."""
    # Validate file_id exists
    file_row = session.get(UploadedFile, req.file_id)
    if not file_row:
        raise HTTPException(
            status_code=404,
            detail={
                "ok": False,
                "error": {
                    "code": "FILE_NOT_FOUND",
                    "message": f"File {req.file_id!r} not found.",
                },
            },
        )

    result = run_agent(
        file_id=req.file_id,
        question=req.question,
        session_id=req.session_id,
    )
    return ok(result)


@router.get("/runs")
def list_runs(
    file_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
) -> dict:
    """List past analysis runs with optional file_id filter and pagination."""
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "error": {
                    "code": "INVALID_LIMIT",
                    "message": "limit must be between 1 and 200",
                },
            },
        )

    q = select(AnalysisRun).order_by(AnalysisRun.created_at.desc()).limit(limit).offset(offset)
    if file_id:
        q = q.where(AnalysisRun.file_id == file_id)

    runs = session.execute(q).scalars().all()

    count_q = select(func.count()).select_from(AnalysisRun)
    if file_id:
        count_q = count_q.where(AnalysisRun.file_id == file_id)
    total = session.execute(count_q).scalar()

    return ok(
        {
            "runs": [
                {
                    "run_id": r.id,
                    "file_id": r.file_id,
                    "question": r.question,
                    "answer": r.answer_text,
                    "chart_spec": json.loads(r.chart_spec_json) if r.chart_spec_json else None,
                    "status": r.status,
                    "error": r.error_message,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                }
                for r in runs
            ],
            "total": total,
        }
    )
