"""Dataset upload + ask router — the analysis API surface.

POST /datasets               — multipart upload of one CSV; validates, stores the
                               raw file locally under data/uploads/, derives and
                               persists schema + bounded sample.
POST /datasets/{id}/ask      — runs the analysis graph synchronously and returns
                               the audited answer.

Data-locality: the uploaded bytes are written to the local filesystem and never
sent anywhere. Only the derived schema + bounded sample ever reach the LLM, and
that boundary is enforced inside the graph — not here.
"""
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from api._common import ok, api_error
from config.settings import get_settings
from db.models import DatasetRow
from db.session import get_session
from domain.analysis import AskRequest, AskResponse, UploadResponse
from graph.runner import run_query
from observability.events import get_logger
from tools.dataset import load_and_describe

router = APIRouter()

_log = get_logger("api.datasets")

# __file__ = src/api/datasets.py → 2 parents up = repo root → data/uploads
_UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "uploads"


@router.post("/datasets")
def upload_dataset(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> dict:
    settings = get_settings()
    filename = file.filename or "upload.csv"

    # 1. Extension gate — Phase 1 accepts .csv only.
    if not filename.lower().endswith(".csv"):
        _log.info("dataset.upload.rejected", reason="bad_extension", filename=filename)
        raise api_error("BAD_FILE", "Only .csv files are accepted.", 400)

    # 2. Read bytes + size gate.
    raw = file.file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(raw) > max_bytes:
        _log.info(
            "dataset.upload.rejected",
            reason="too_large",
            size_bytes=len(raw),
            max_upload_mb=settings.max_upload_mb,
        )
        raise api_error(
            "TOO_LARGE",
            f"The upload exceeds the {settings.max_upload_mb} MB limit.",
            413,
        )

    # 3. Persist the raw bytes locally (data stays on the box).
    dataset_id = str(uuid4())
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = _UPLOAD_DIR / f"{dataset_id}.csv"
    dest.write_bytes(raw)

    # 4. Validate it parses + derive schema/sample. On failure, delete the bad
    #    file and return a graceful 400 — never a stack trace.
    try:
        described = load_and_describe(str(dest))
    except ValueError as exc:
        _safe_unlink(dest)
        _log.info("dataset.upload.rejected", reason="unparseable", filename=filename)
        raise api_error("BAD_FILE", str(exc), 400)
    except Exception as exc:  # defensive: any unexpected parse failure
        _safe_unlink(dest)
        _log.error("dataset.upload.error", filename=filename, error=str(exc))
        raise api_error(
            "BAD_FILE", "Could not read this file as a CSV.", 400
        )

    # 5. Persist the DatasetRow (metadata only; the file stays on disk).
    row = DatasetRow(
        id=dataset_id,
        filename=filename,
        source_format="csv",
        file_path=str(dest),
        row_count=described["row_count"],
        schema_json=described["schema"],
        sample_json=described["sample"],
        size_bytes=len(raw),
    )
    session.add(row)
    session.flush()

    _log.info(
        "dataset.uploaded",
        dataset_id=dataset_id,
        filename=filename,
        row_count=described["row_count"],
        size_bytes=len(raw),
    )

    payload = UploadResponse.model_validate(
        {
            "dataset_id": dataset_id,
            "filename": filename,
            "row_count": described["row_count"],
            "schema": described["schema"],
            "sample_preview": described["sample"]["preview_rows"],
        }
    )
    return ok(payload.model_dump(by_alias=True))


@router.post("/datasets/{dataset_id}/ask")
def ask_dataset(
    dataset_id: str,
    req: AskRequest,
    session: Session = Depends(get_session),
) -> dict:
    # 1. Unknown dataset → 404.
    dataset = session.get(DatasetRow, dataset_id)
    if dataset is None:
        _log.info("dataset.ask.not_found", dataset_id=dataset_id)
        raise api_error("NOT_FOUND", f"Dataset {dataset_id} not found.", 404)

    # 2. Empty/whitespace question → 400.
    question = (req.question or "").strip()
    if not question:
        _log.info("dataset.ask.bad_request", dataset_id=dataset_id)
        raise api_error("BAD_REQUEST", "The question must not be empty.", 400)

    _log.info(
        "dataset.ask",
        dataset_id=dataset_id,
        conversation_id=req.conversation_id,
    )

    # 3. Run the graph synchronously. A graph-level failure comes back as a dict
    #    with status="failed" and a human-readable error — that is a 200 failed
    #    envelope, NOT an HTTP 500. Any unexpected exception is also wrapped into
    #    a graceful failed envelope so the client never sees a stack trace.
    try:
        result = run_query(dataset_id, question, req.conversation_id)
    except Exception as exc:  # defensive — the graph already handles its own errors
        _log.error("dataset.ask.error", dataset_id=dataset_id, error=str(exc))
        result = {
            "query_id": "",
            "dataset_id": dataset_id,
            "status": "failed",
            "answer": None,
            "explanation": None,
            "code": None,
            "result": None,
            "error": "Could not compute an answer for this question.",
            "model": None,
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "latency_ms": 0.0,
        }

    payload = AskResponse(**result)
    return ok(payload.model_dump())


def _safe_unlink(path: Path) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
