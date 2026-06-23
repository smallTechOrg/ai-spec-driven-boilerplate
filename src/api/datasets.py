import json
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import select

from api._common import ok, api_error
from db.session import get_session
from db.models import SessionRow, DatasetRow
from db.duckdb_loader import load_dataset_schema

router = APIRouter(prefix="/datasets", tags=["datasets"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "uploads"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".json"}


@router.post("/", status_code=201)
def upload_dataset(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> dict:
    # Validate session exists
    sess_row = session.get(SessionRow, session_id)
    if sess_row is None:
        raise api_error("SESSION_NOT_FOUND", f"Session {session_id!r} not found", 404)

    # Validate file extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise api_error(
            "UNSUPPORTED_FILE_TYPE",
            f"File type {suffix!r} not supported. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
            400,
        )
    file_type = suffix.lstrip(".")

    # Create session upload directory
    session_upload_dir = UPLOAD_DIR / session_id
    try:
        session_upload_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise api_error("FILESYSTEM_ERROR", f"Could not create upload directory: {exc}", 500)

    file_path = session_upload_dir / file.filename

    # Write file to disk
    try:
        with open(file_path, "wb") as out:
            shutil.copyfileobj(file.file, out)
    except OSError as exc:
        raise api_error("FILESYSTEM_ERROR", f"Could not write uploaded file: {exc}", 500)
    finally:
        file.file.close()

    # Check file size after write
    size_bytes = file_path.stat().st_size
    if size_bytes > MAX_FILE_SIZE:
        file_path.unlink(missing_ok=True)
        raise api_error(
            "FILE_TOO_LARGE",
            f"File size {size_bytes} bytes exceeds limit of {MAX_FILE_SIZE} bytes",
            400,
        )

    # Load schema via DuckDB
    try:
        schema = load_dataset_schema(str(file_path), file_type)
    except (ValueError, RuntimeError) as exc:
        file_path.unlink(missing_ok=True)
        raise api_error("PARSE_ERROR", str(exc), 400)
    except Exception as exc:
        file_path.unlink(missing_ok=True)
        raise api_error("PARSE_ERROR", f"Failed to parse file: {exc}", 400)

    # Persist DatasetRow
    columns_json = json.dumps(schema["columns"])
    ds = DatasetRow(
        session_id=session_id,
        name=file.filename,
        file_path=str(file_path),
        file_type=file_type,
        row_count=schema["row_count"],
        columns_json=columns_json,
        size_bytes=size_bytes,
    )
    session.add(ds)
    session.flush()

    return ok({
        "dataset_id": ds.id,
        "name": ds.name,
        "row_count": ds.row_count,
        "columns": schema["columns"],
        "uploaded_at": ds.uploaded_at.isoformat(),
    })


@router.get("/", status_code=200)
def list_datasets(
    session_id: str,
    session: Session = Depends(get_session),
) -> dict:
    # Validate session exists
    sess_row = session.get(SessionRow, session_id)
    if sess_row is None:
        raise api_error("SESSION_NOT_FOUND", f"Session {session_id!r} not found", 404)

    rows = session.scalars(
        select(DatasetRow).where(DatasetRow.session_id == session_id)
    ).all()

    result = []
    for ds in rows:
        try:
            columns = json.loads(ds.columns_json)
        except Exception:
            columns = []
        result.append({
            "dataset_id": ds.id,
            "name": ds.name,
            "row_count": ds.row_count,
            "columns": columns,
            "uploaded_at": ds.uploaded_at.isoformat(),
        })

    return ok(result)
