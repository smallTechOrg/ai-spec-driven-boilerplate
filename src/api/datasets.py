"""Dataset upload endpoint — POST /api/datasets (Phase 1, REAL)."""
from __future__ import annotations

import json

import structlog
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from api._common import api_error, ok
from config.settings import get_settings
from data.ingest import FileTooLargeError, IngestError, ingest_file
from db.models import Dataset
from db.session import get_session
from domain.dataset import UploadResponse

log = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/api/datasets")
async def upload_dataset(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> dict:
    settings = get_settings()
    filename = file.filename or "upload"
    content = await file.read()

    try:
        ingested = ingest_file(
            filename=filename,
            content=content,
            storage_dir=settings.data_dir,
            max_bytes=settings.max_upload_bytes,
        )
    except FileTooLargeError as exc:
        raise api_error("FILE_TOO_LARGE", str(exc), 413)
    except IngestError as exc:
        raise api_error("BAD_FILE", str(exc), 400)
    except Exception as exc:  # noqa: BLE001 — DuckDB load/profile failure
        log.error("upload_failed", filename=filename, error=str(exc))
        raise api_error("LOAD_FAILED", f"Could not load the file: {exc}", 500)

    for d in ingested:
        session.add(
            Dataset(
                id=d.id,
                name=d.name,
                source_path=d.source_path,
                source_kind=d.source_kind,
                sheet_name=d.sheet_name,
                duckdb_table=d.duckdb_table,
                profile_json=json.dumps(d.profile),
                row_count=d.row_count,
                size_bytes=d.size_bytes,
            )
        )

    return ok(UploadResponse.from_ingested(ingested).model_dump())
