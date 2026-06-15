import shutil
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from data_analysis_agent.api import templates
from data_analysis_agent.api._common import api_error, render
from data_analysis_agent.config.settings import get_settings
from data_analysis_agent.db.models import DatasetRow, QueryRecordRow
from data_analysis_agent.db.session import get_session

log = structlog.get_logger()
router = APIRouter()


@router.get("/")
def home(request: Request):
    return render(request, templates, "home.html")


@router.post("/upload")
def upload_csv(
    request: Request,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise api_error("INVALID_FILE", "Only CSV files are supported.")

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    dataset = DatasetRow(filename=file.filename, file_path="")
    session.add(dataset)
    session.flush()

    dest = upload_dir / f"{dataset.id}.csv"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    dataset.file_path = str(dest)
    log.info("upload.success", dataset_id=dataset.id, filename=file.filename)

    return RedirectResponse(url=f"/datasets/{dataset.id}", status_code=303)


@router.get("/datasets/{dataset_id}")
def dataset_detail(request: Request, dataset_id: str, session: Session = Depends(get_session)):
    dataset = session.get(DatasetRow, dataset_id)
    if not dataset:
        raise api_error("NOT_FOUND", "Dataset not found.", status_code=404)
    return render(request, templates, "dataset.html", dataset=dataset)


@router.post("/datasets/{dataset_id}/query")
def submit_query(
    request: Request,
    dataset_id: str,
    question: str = Form(...),
    session: Session = Depends(get_session),
):
    if not question.strip():
        raise api_error("EMPTY_QUESTION", "Question cannot be empty.")

    dataset = session.get(DatasetRow, dataset_id)
    if not dataset:
        raise api_error("NOT_FOUND", "Dataset not found.", status_code=404)

    qr = QueryRecordRow(dataset_id=dataset_id, question=question.strip())
    session.add(qr)
    session.flush()
    query_record_id = qr.id
    session.commit()

    try:
        from data_analysis_agent.graph.runner import run_pipeline
        final_state = run_pipeline(
            query_record_id=query_record_id,
            dataset_id=dataset_id,
            question=question.strip(),
            csv_path=dataset.file_path,
        )

        if final_state.get("error"):
            log.error("query.pipeline_error", error=final_state["error"])
            return render(
                request, templates, "error.html",
                detail=final_state["error"],
            )

        # Re-fetch so we get the committed answer
        session.expire_all()
        qr_updated = session.get(QueryRecordRow, query_record_id)
        return render(
            request, templates, "answer.html",
            dataset=dataset,
            query_record=qr_updated,
        )

    except Exception as exc:
        log.error("query.unexpected_error", error=str(exc))
        return render(request, templates, "error.html", detail=str(exc))


@router.get("/datasets/{dataset_id}/history")
def query_history(
    request: Request, dataset_id: str, session: Session = Depends(get_session)
):
    dataset = session.get(DatasetRow, dataset_id)
    if not dataset:
        raise api_error("NOT_FOUND", "Dataset not found.", status_code=404)
    records = (
        session.query(QueryRecordRow)
        .filter(QueryRecordRow.dataset_id == dataset_id)
        .order_by(QueryRecordRow.created_at.desc())
        .all()
    )
    return render(
        request, templates, "history.html",
        dataset=dataset,
        records=records,
    )
