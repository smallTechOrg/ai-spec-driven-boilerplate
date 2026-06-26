import io
import json
import logging
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from api._common import ok, api_error
from db.models import DatasetRow, SessionRow
from db.session import get_session
from domain.dataset import DatasetListResponse, DatasetResponse
from domain.query import QueryRequest, QueryResponse
from domain.session import SessionResponse
from graph.runner import run_agent

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/sessions")
def create_session(db: Session = Depends(get_session)) -> dict:
    row = SessionRow()
    db.add(row)
    db.flush()
    return ok(SessionResponse(session_id=row.id, created_at=row.created_at).model_dump())


@router.post("/sessions/{session_id}/datasets")
async def upload_dataset(
    session_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
) -> dict:
    # Validate session
    sess = db.get(SessionRow, session_id)
    if sess is None:
        raise api_error("SESSION_NOT_FOUND", f"Session {session_id} not found", 404)

    # Validate file extension
    filename = file.filename or "upload.csv"
    if not filename.lower().endswith(".csv"):
        raise api_error("INVALID_FILE_TYPE", "Only .csv files are supported", 422)

    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise api_error("FILE_TOO_LARGE", "File exceeds 50 MB limit", 413)

    # Parse with pandas to validate and extract metadata
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise api_error("INVALID_FILE_TYPE", f"Could not parse CSV: {exc}", 422)

    row_count = len(df)
    column_names = list(df.columns)

    # Persist row first to get ID
    dataset_row = DatasetRow(
        session_id=session_id,
        filename=filename,
        row_count=row_count,
        column_names=json.dumps(column_names),
        file_path="",  # set after flush to get ID
    )
    db.add(dataset_row)
    db.flush()

    # Save to disk
    upload_dir = Path("data/uploads") / session_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    file_path = str(upload_dir / f"{dataset_row.id}_{safe_filename}")
    Path(file_path).write_bytes(content)

    dataset_row.file_path = file_path
    db.flush()

    return ok(DatasetResponse(
        dataset_id=dataset_row.id,
        session_id=session_id,
        filename=filename,
        row_count=row_count,
        column_names=column_names,
        created_at=dataset_row.created_at,
    ).model_dump())


@router.get("/sessions/{session_id}/datasets")
def list_datasets(session_id: str, db: Session = Depends(get_session)) -> dict:
    sess = db.get(SessionRow, session_id)
    if sess is None:
        raise api_error("SESSION_NOT_FOUND", f"Session {session_id} not found", 404)

    rows = db.query(DatasetRow).filter(DatasetRow.session_id == session_id).all()
    datasets = [
        DatasetResponse(
            dataset_id=r.id,
            session_id=r.session_id,
            filename=r.filename,
            row_count=r.row_count,
            column_names=json.loads(r.column_names),
            created_at=r.created_at,
        )
        for r in rows
    ]
    return ok(DatasetListResponse(datasets=datasets).model_dump())


@router.post("/sessions/{session_id}/queries")
def run_query(
    session_id: str,
    req: QueryRequest,
    db: Session = Depends(get_session),
) -> dict:
    sess = db.get(SessionRow, session_id)
    if sess is None:
        raise api_error("SESSION_NOT_FOUND", f"Session {session_id} not found", 404)

    if not req.question.strip():
        raise api_error("EMPTY_QUESTION", "Question must not be empty", 422)

    ds = db.get(DatasetRow, req.dataset_id)
    if ds is None or ds.session_id != session_id:
        raise api_error("DATASET_NOT_FOUND", f"Dataset {req.dataset_id} not found in this session", 404)

    result = run_agent(session_id=session_id, dataset_id=req.dataset_id, question=req.question)

    if result["status"] == "failed":
        raise api_error("QUERY_FAILED", result.get("error") or "Query failed", 422)

    return ok(QueryResponse(**result).model_dump())
