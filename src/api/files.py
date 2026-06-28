import json
import logging
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api._common import ok
from db.models import UploadedFile
from db.session import get_session
from domain.file import SchemaPreview, UploadedFileResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])

_MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
_ALLOWED_EXTENSIONS = {".csv"}

# Repo root is three levels up from src/api/files.py
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_UPLOAD_DIR = _REPO_ROOT / "data" / "uploads"


def _file_id() -> str:
    return str(uuid4())


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> dict:
    # 1. Validate extension
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": (
                    f"File type '{suffix}' is not supported in Phase 1. "
                    "Only .csv files are accepted."
                ),
            },
        )

    # 2. Read content
    content = await file.read()

    # 3. Validate not empty
    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail={"code": "EMPTY_FILE", "message": "The uploaded file is empty."},
        )

    # 4. Validate size < 100 MB
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": "File exceeds the 100 MB limit.",
            },
        )

    # 5. Parse with pandas
    import io

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        logger.warning("CSV parse error for %s: %s", filename, exc)
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MALFORMED_CSV",
                "message": "The file could not be parsed as a valid CSV.",
            },
        )

    # 6. Extract schema
    columns = df.columns.tolist()
    dtypes = df.dtypes.apply(str).to_dict()
    head = df.head(3)
    sample_rows = head.where(pd.notnull(head), None).values.tolist()
    row_count = len(df)
    file_size_bytes = len(content)

    schema_preview = SchemaPreview(
        columns=columns,
        dtypes=dtypes,
        sample_rows=sample_rows,
    )
    schema_json = json.dumps(schema_preview.model_dump())

    # 7. Write to data/uploads/<uuid>/<filename>
    file_id = _file_id()
    dest_dir = _UPLOAD_DIR / file_id
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / filename
        dest_path.write_bytes(content)
    except OSError as exc:
        logger.error("Filesystem write error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "FILESYSTEM_ERROR",
                "message": "Failed to write file to disk.",
            },
        )

    # 8. Insert UploadedFile row
    try:
        row = UploadedFile(
            id=file_id,
            original_name=filename,
            file_path=str(dest_path),
            source_type="csv",
            row_count=row_count,
            file_size_bytes=file_size_bytes,
            schema_json=schema_json,
        )
        session.add(row)
        session.flush()  # get created_at populated
        session.refresh(row)
    except Exception as exc:
        logger.error("DB insert error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "DB_ERROR",
                "message": "Failed to record file in the database.",
            },
        )

    response = UploadedFileResponse(
        file_id=row.id,
        original_name=row.original_name,
        source_type=row.source_type,
        row_count=row.row_count,
        file_size_bytes=row.file_size_bytes,
        schema_preview=schema_preview,
        created_at=row.created_at,
    )
    return ok(response.model_dump())


@router.get("")
def list_files(session: Session = Depends(get_session)) -> dict:
    rows = session.query(UploadedFile).order_by(UploadedFile.created_at.asc()).all()
    files = []
    for row in rows:
        try:
            schema_dict = json.loads(row.schema_json) if row.schema_json else {}
            schema_preview = SchemaPreview(**schema_dict)
        except Exception:
            schema_preview = SchemaPreview(columns=[], dtypes={}, sample_rows=[])

        files.append(
            UploadedFileResponse(
                file_id=row.id,
                original_name=row.original_name,
                source_type=row.source_type,
                row_count=row.row_count,
                file_size_bytes=row.file_size_bytes,
                schema_preview=schema_preview,
                created_at=row.created_at,
            ).model_dump()
        )

    return ok({"files": files})
