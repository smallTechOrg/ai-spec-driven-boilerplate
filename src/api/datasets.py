"""Dataset upload + fetch (Phase 1)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from analysis.profile import build_profile, load_csv
from api._common import api_error, ok
from db.models import DatasetRow
from db.session import get_session

router = APIRouter()

# 100MB upload cap (roadmap: datasets up to ~100MB).
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
_UPLOAD_ROOT = Path(__file__).resolve().parent.parent.parent / "uploads"


def _dataset_payload(ds: DatasetRow) -> dict:
    return {
        "id": ds.id,
        "name": ds.name,
        "file_type": ds.file_type,
        "row_count": ds.row_count,
        "size_bytes": ds.size_bytes,
        "profile": json.loads(ds.profile_json),
        "created_at": ds.created_at.isoformat(),
    }


def _profile_file(file_path: str) -> tuple[int, dict]:
    """Heavy pandas work — run off the event loop."""
    df = load_csv(file_path)
    if df.shape[0] == 0 or df.shape[1] == 0:
        raise ValueError("The file has no usable rows/columns")
    profile = build_profile(df)
    return len(df), profile


@router.post("/datasets")
async def upload_dataset(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> dict:
    filename = file.filename or ""
    if not filename:
        raise api_error("BAD_UPLOAD", "No file provided", 400)
    if not filename.lower().endswith(".csv"):
        raise api_error("BAD_UPLOAD", "Only CSV files are supported in Phase 1", 400)

    dataset_id = str(uuid4())
    dest_dir = _UPLOAD_ROOT / dataset_id
    dest_path = dest_dir / filename

    # Save the raw file to disk.
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        size = 0
        with dest_path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise api_error("FILE_TOO_LARGE", "File exceeds the 100MB limit", 413)
                out.write(chunk)
    except HTTPException:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise api_error("PROFILE_FAILED", f"Failed to save upload: {exc}", 500)

    # Profile it (off the event loop).
    try:
        row_count, profile = await run_in_threadpool(_profile_file, str(dest_path))
    except Exception as exc:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise api_error("BAD_UPLOAD", f"Could not parse the spreadsheet: {exc}", 400)

    ds = DatasetRow(
        id=dataset_id,
        name=filename,
        file_path=str(dest_path),
        file_type="csv",
        size_bytes=size,
        row_count=row_count,
        profile_json=json.dumps(profile, default=str),
    )
    session.add(ds)
    session.flush()
    return ok(_dataset_payload(ds))


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str, session: Session = Depends(get_session)) -> dict:
    ds = session.get(DatasetRow, dataset_id)
    if ds is None:
        raise api_error("NOT_FOUND", f"Dataset {dataset_id} not found", 404)
    return ok(_dataset_payload(ds))
