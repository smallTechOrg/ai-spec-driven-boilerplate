from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from api._common import ok, api_error
from db.session import get_session
from db.models import RunRow
from datasets.store import save_dataset, get_dataset, DatasetError
from domain.dataset import (
    ColumnSchema,
    UploadResponse,
    AskRequest,
    AskResponse,
)
from observability.events import get_logger

import json

router = APIRouter()
logger = get_logger("api.datasets")

# Human-readable copy for graceful (200 + status:"failed") ask failures.
_UNKNOWN_DATASET_COPY = "We couldn't find that dataset. Please upload your CSV again."
_RUN_FAILURE_COPY = "Could not reach the analysis model — please retry."


@router.post("/datasets")
async def upload_dataset(file: UploadFile = File(...)) -> dict:
    filename = file.filename or "upload.csv"
    try:
        file_bytes = await file.read()
    except Exception as exc:  # noqa: BLE001
        logger.warning("upload_read_failed", filename=filename, error=str(exc))
        raise api_error("UPLOAD_READ_FAILED", "Could not read the uploaded file.", 400)

    try:
        row = save_dataset(file_bytes, filename)
    except DatasetError as exc:
        raise api_error("BAD_UPLOAD", exc.message, 400)
    except Exception as exc:  # noqa: BLE001
        logger.error("upload_failed", filename=filename, error=str(exc))
        raise api_error(
            "UPLOAD_FAILED", "Could not store the uploaded file. Please try again.", 500
        )

    schema = [ColumnSchema(**col) for col in json.loads(row.schema_json)]
    resp = UploadResponse(
        dataset_id=row.id,
        filename=row.filename,
        row_count=row.row_count,
        schema=schema,
    )
    return ok(resp.model_dump())


@router.post("/datasets/{dataset_id}/ask")
def ask_dataset(
    dataset_id: str,
    req: AskRequest,
    session: Session = Depends(get_session),
) -> dict:
    question = (req.question or "").strip()
    if not question:
        raise api_error("EMPTY_QUESTION", "Please enter a question to ask.", 400)

    # Unknown dataset → graceful 200 + status:"failed" (no LLM call needed).
    if get_dataset(session, dataset_id) is None:
        logger.info("ask_unknown_dataset", dataset_id=dataset_id)
        resp = AskResponse(
            run_id=None,
            dataset_id=dataset_id,
            status="failed",
            answer=None,
            error=_UNKNOWN_DATASET_COPY,
        )
        return ok(resp.model_dump())

    # Defer the runner import so the route stays importable before backend-agent
    # wires the new runner signature.
    from graph.runner import run_agent

    try:
        run_id = run_agent(dataset_id, question)
    except Exception as exc:  # noqa: BLE001 - graceful failure, never a stack trace
        logger.error("ask_run_failed", dataset_id=dataset_id, error=str(exc))
        resp = AskResponse(
            run_id=None,
            dataset_id=dataset_id,
            status="failed",
            answer=None,
            error=_RUN_FAILURE_COPY,
        )
        return ok(resp.model_dump())

    run = session.get(RunRow, run_id)
    if run is None:
        resp = AskResponse(
            run_id=run_id,
            dataset_id=dataset_id,
            status="failed",
            answer=None,
            error=_RUN_FAILURE_COPY,
        )
        return ok(resp.model_dump())

    resp = AskResponse(
        run_id=run.id,
        dataset_id=dataset_id,
        status=run.status,
        answer=run.output_text,
        error=run.error_message,
    )
    return ok(resp.model_dump())
