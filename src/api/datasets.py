from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from analysis.loader import clear_cache
from analysis.profile import kind_for_filename
from api._common import api_error, ok
from api._serializers import dataset_with_profile, run_body
from config.settings import get_settings
from db.models import AnalysisRun, Dataset, DatasetProfile
from db.session import get_session
from domain.analysis import AskRequest
from graph.runner import profile_and_store, run_analysis

router = APIRouter()


def _latest_profile(session: Session, dataset_id: str) -> DatasetProfile | None:
    return (
        session.query(DatasetProfile)
        .filter(DatasetProfile.dataset_id == dataset_id)
        .order_by(DatasetProfile.created_at.desc())
        .first()
    )


@router.post("/datasets")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    session: Session = Depends(get_session),
) -> dict:
    filename = file.filename or "upload"
    kind = kind_for_filename(filename)
    if kind is None:
        raise api_error(
            "UNSUPPORTED_TYPE",
            "Unsupported file type. Upload a .csv or .xlsx file.",
            400,
        )

    contents = await file.read()
    dataset_id = str(uuid4())
    upload_root = Path(get_settings().upload_dir) / dataset_id
    upload_root.mkdir(parents=True, exist_ok=True)
    dest = upload_root / filename
    dest.write_bytes(contents)

    try:
        dataset, profile = profile_and_store(
            session,
            name=name or filename,
            kind=kind,
            file_path=str(dest),
            size_bytes=len(contents),
            dataset_id=dataset_id,
        )
    except Exception as exc:
        raise api_error("UNREADABLE_FILE", f"Could not read or profile file: {exc}", 400)

    return ok(dataset_with_profile(dataset, profile))


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str, session: Session = Depends(get_session)) -> dict:
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise api_error("NOT_FOUND", f"Dataset {dataset_id} not found", 404)
    profile = _latest_profile(session, dataset_id)
    if profile is None:
        raise api_error("NOT_FOUND", f"Profile for dataset {dataset_id} not found", 404)
    return ok(dataset_with_profile(dataset, profile))


@router.post("/datasets/{dataset_id}/ask")
def ask_dataset(
    dataset_id: str,
    req: AskRequest,
    session: Session = Depends(get_session),
) -> dict:
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise api_error("NOT_FOUND", f"Dataset {dataset_id} not found", 404)

    # A re-upload could shift cached frames; keep cache coherent per dataset path.
    clear_cache()
    run_id = run_analysis(dataset_id, req.question)

    run = session.get(AnalysisRun, run_id)
    if run is None:
        raise api_error("RUN_LOST", "Run not found after creation", 500)
    # honest compute failure still returns 200 with status="failed"
    return ok({"run": run_body(run)})
