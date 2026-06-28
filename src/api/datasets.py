"""Dataset upload + profiling endpoints.

Phase 1: store the file, compute schema + sample. Phase 2: also compute the full
per-column auto-profile (type/range/distinct/missing) over the full file locally
and persist it. Profiling the full file is best-effort: a failure degrades to a
null profile but never fails the upload.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from analyst.profile import compute_profile, profile_csv
from api._common import ok, api_error
from db.models import DatasetRow
from db.session import get_session
from observability.events import get_logger

router = APIRouter()
_log = get_logger("api.datasets")

# src/api/datasets.py -> parent.parent = src/  -> data/datasets
_DATASETS_DIR = Path(__file__).resolve().parent.parent / "data" / "datasets"


@router.post("/datasets")
def upload_dataset(
    file: UploadFile = File(...), session: Session = Depends(get_session)
) -> dict:
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise api_error("BAD_REQUEST", "Only .csv files are supported.", 400)

    dataset_id = str(uuid4())
    dest_dir = _DATASETS_DIR / dataset_id
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / Path(filename).name
        with dest_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    except Exception as exc:
        _log.error("upload_write_failed", error=str(exc))
        raise api_error("DISK_ERROR", f"Could not save file: {exc}", 500)

    if dest_path.stat().st_size == 0:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise api_error("BAD_REQUEST", "Uploaded file is empty.", 400)

    try:
        prof = profile_csv(str(dest_path))
    except ValueError as exc:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise api_error("BAD_REQUEST", str(exc), 400)
    except Exception as exc:
        _log.error("profile_failed", error=str(exc))
        raise api_error("PROFILE_ERROR", f"Failed to profile CSV: {exc}", 500)

    # Phase 2: full per-column auto-profile over the FULL file (local pandas).
    # Best-effort — a failure must NOT fail the upload (degrade to null profile).
    profile: list[dict] | None = None
    prof_started = time.monotonic()
    try:
        profile = compute_profile(str(dest_path))
        prof_latency = int((time.monotonic() - prof_started) * 1000)
        _log.info("dataset_profiled", dataset_id=dataset_id,
                  columns=len(profile), latency_ms=prof_latency)
    except Exception as exc:
        prof_latency = int((time.monotonic() - prof_started) * 1000)
        _log.error("auto_profile_failed", dataset_id=dataset_id,
                   error=str(exc), latency_ms=prof_latency)
        profile = None

    ds = DatasetRow(
        id=dataset_id,
        filename=Path(filename).name,
        path=str(dest_path),
        row_count=prof.row_count,
        schema_json=json.dumps(prof.schema),
        sample_json=json.dumps(prof.sample_rows),
        profile_json=json.dumps(profile) if profile is not None else None,
    )
    session.add(ds)
    session.flush()

    _log.info("dataset_uploaded", dataset_id=dataset_id,
              filename=ds.filename, row_count=prof.row_count,
              profiled=profile is not None)

    return ok({
        "dataset_id": dataset_id,
        "filename": ds.filename,
        "row_count": prof.row_count,
        "schema": prof.schema,
        "sample": prof.sample_rows,
        "profile": profile,
    })
