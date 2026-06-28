"""Dataset upload + profile endpoint. Response shape per spec/api.md (raw JSON)."""
from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from api._common import api_error
from db.session import get_session
from db.models import Dataset
from config.settings import get_settings
from analysis.profile import build_profile

router = APIRouter()

_MAX_BYTES = 100 * 1024 * 1024  # ~100MB


def _data_dir() -> Path:
    d = Path(get_settings().data_dir) / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.post("/api/datasets")
async def upload_dataset(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> dict:
    filename = file.filename or "upload.csv"
    if not filename.lower().endswith(".csv"):
        raise api_error("BAD_REQUEST", "Only .csv files are supported in Phase 1.", 400)

    raw = await file.read()
    if len(raw) > _MAX_BYTES:
        raise api_error("BAD_REQUEST", "File exceeds the ~100MB limit.", 400)
    if not raw.strip():
        raise api_error("BAD_REQUEST", "Uploaded file is empty.", 400)

    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:
        raise api_error("BAD_REQUEST", f"Could not parse CSV: {exc}", 400)

    if df.shape[0] == 0 or df.shape[1] == 0:
        raise api_error("BAD_REQUEST", "CSV has no data rows or columns.", 400)

    try:
        settings = get_settings()
        profile = build_profile(df, sample_rows=settings.sample_rows)

        dataset_id = str(uuid4())
        storage_path = _data_dir() / f"{dataset_id}.csv"
        storage_path.write_bytes(raw)

        row = Dataset(
            id=dataset_id,
            filename=filename,
            storage_path=str(storage_path),
            row_count=int(df.shape[0]),
            column_count=int(df.shape[1]),
            size_bytes=len(raw),
            profile=profile,
        )
        session.add(row)
        session.flush()
    except Exception as exc:
        raise api_error("PROFILE_FAILED", f"Profiling failed: {exc}", 500)

    return {
        "id": dataset_id,
        "filename": filename,
        "row_count": int(df.shape[0]),
        "column_count": int(df.shape[1]),
        "size_bytes": len(raw),
        "profile": profile,
    }
