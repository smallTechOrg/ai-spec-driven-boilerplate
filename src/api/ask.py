"""Ask endpoint — POST /api/ask (Phase 1, REAL).

A failed run is HTTP 200 with status="failed" and the attempted SQL + error
inside `data`, so the UI always shows what was tried. Transport-level failures
(missing dataset, bad request) use api_error.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter

from api._common import api_error, ok
from domain.ask import AskRequest
from graph.runner import DatasetNotFound, ask as run_ask

log = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/api/ask")
def ask(req: AskRequest) -> dict:
    if not req.dataset_id or not req.dataset_id.strip():
        raise api_error("BAD_REQUEST", "dataset_id is required", 400)
    if not req.question or not req.question.strip():
        raise api_error("BAD_REQUEST", "question is required", 400)

    try:
        response = run_ask(req.dataset_id, req.question)
    except DatasetNotFound:
        raise api_error("NOT_FOUND", f"Dataset {req.dataset_id} not found", 404)
    except Exception as exc:  # noqa: BLE001 — unexpected runner failure
        log.error("ask_failed", dataset_id=req.dataset_id, error=str(exc))
        raise api_error("ASK_FAILED", f"Ask failed: {exc}", 500)

    # Graph errors surface as 200 with status="failed" (handled in the response).
    return ok(response.model_dump())
