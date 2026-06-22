from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from data_analyst.api._common import api_error
from data_analyst.db.models import Dataset
from data_analyst.db.session import get_session
from data_analyst.domain.schemas import DatasetListResponse, DatasetResponse
from data_analyst.duckdb_service import get_duckdb_service

router = APIRouter()
logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
_MAX_FILE_BYTES = 200 * 1024 * 1024  # 200 MB


def _sanitise_table_name(name: str) -> str:
    """Produce a valid SQL identifier from an arbitrary user-supplied name."""
    lower = name.lower()
    # Replace any non-alphanumeric character (including spaces, hyphens, dots) with _
    sanitised = re.sub(r"[^a-z0-9_]", "_", lower)
    # Collapse consecutive underscores
    sanitised = re.sub(r"_+", "_", sanitised).strip("_")
    # Must start with a letter or underscore
    if sanitised and sanitised[0].isdigit():
        sanitised = "_" + sanitised
    # Truncate to 63 characters (PostgreSQL/DuckDB identifier limit)
    return sanitised[:63] or "_table"


def _unique_table_name(base: str, db: Session) -> str:
    """Append numeric suffix until the table_name is unique among active datasets."""
    candidate = base
    counter = 2
    while (
        db.query(Dataset)
        .filter(Dataset.table_name == candidate, Dataset.is_active == True)  # noqa: E712
        .first()
        is not None
    ):
        candidate = f"{base[:60]}_{counter}"
        counter += 1
    return candidate


def _infer_schema(df: object) -> list[dict]:
    """Return [{column, dtype}] from a pandas DataFrame."""
    import pandas as pd  # noqa: F401

    result = []
    for col in df.columns:  # type: ignore[union-attr]
        result.append({"column": str(col), "dtype": str(df[col].dtype)})  # type: ignore[union-attr]
    return result


@router.post("/datasets", status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(default=None),
    db: Session = Depends(get_session),
) -> JSONResponse:
    import pandas as pd
    from uuid import uuid4

    # Validate name length
    if not name or len(name) > 100:
        raise api_error("INVALID_NAME", "name must be 1–100 characters", 422)

    if description and len(description) > 500:
        raise api_error("INVALID_DESCRIPTION", "description must be ≤ 500 characters", 422)

    # Validate extension
    original_filename = file.filename or "upload"
    ext = Path(original_filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise api_error(
            "UNSUPPORTED_FILE_TYPE",
            f"Unsupported file type '{ext}'. Accepted: .csv, .xlsx, .xls",
            415,
        )

    # Read file content and enforce size limit
    content = await file.read()
    if len(content) > _MAX_FILE_BYTES:
        raise api_error(
            "FILE_TOO_LARGE",
            f"File exceeds the 200 MB limit ({len(content) // 1024 // 1024} MB received)",
            413,
        )

    dataset_id = str(uuid4())
    from data_analyst.config.settings import get_settings
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save the original file
    original_file_path = upload_dir / f"{dataset_id}{ext}"
    try:
        original_file_path.write_bytes(content)
    except OSError as exc:
        logger.error("Failed to write upload file: %s", exc)
        raise api_error("DISK_WRITE_ERROR", "Failed to save file to disk", 500)

    # The path DuckDB will read from (always a CSV for Excel uploads)
    duckdb_file_path = str(original_file_path)
    csv_path: Path | None = None
    info: str | None = None

    try:
        if ext in (".xlsx", ".xls"):
            # Convert to CSV so DuckDB can use read_csv_auto
            df = pd.read_excel(original_file_path, sheet_name=0, engine="openpyxl" if ext == ".xlsx" else None)
            info = "Only the first sheet was loaded from the Excel file."
            csv_path = upload_dir / f"{dataset_id}.csv"
            df.to_csv(csv_path, index=False)
            duckdb_file_path = str(csv_path)
        else:
            df = pd.read_csv(original_file_path)
    except Exception as exc:
        original_file_path.unlink(missing_ok=True)
        if csv_path is not None:
            csv_path.unlink(missing_ok=True)
        logger.error("Failed to parse uploaded file: %s", exc)
        raise api_error("UNPARSEABLE_FILE", f"Could not parse file: {exc}", 422)

    # Require at least one column (completely empty file has no headers)
    if len(df.columns) == 0:
        original_file_path.unlink(missing_ok=True)
        if csv_path is not None:
            csv_path.unlink(missing_ok=True)
        raise api_error("UNPARSEABLE_FILE", "File has no column headers", 422)

    schema = _infer_schema(df)
    row_count = len(df)
    column_count = len(df.columns)

    # Derive table_name
    base_name = _sanitise_table_name(name)
    table_name = _unique_table_name(base_name, db)

    # Insert SQLite row
    dataset = Dataset(
        id=dataset_id,
        name=name,
        description=description,
        table_name=table_name,
        original_filename=original_filename,
        file_path=duckdb_file_path,
        file_extension=ext,
        row_count=row_count,
        column_count=column_count,
        schema_json=json.dumps(schema),
        is_active=True,
    )
    db.add(dataset)
    try:
        db.flush()
    except Exception as exc:
        original_file_path.unlink(missing_ok=True)
        if csv_path is not None:
            csv_path.unlink(missing_ok=True)
        logger.error("SQLite insert failed: %s", exc)
        raise api_error("DB_ERROR", "Failed to save dataset metadata", 500)

    # Register DuckDB view
    try:
        svc = get_duckdb_service()
        svc.register_dataset(dataset)
    except Exception as exc:
        original_file_path.unlink(missing_ok=True)
        if csv_path is not None:
            csv_path.unlink(missing_ok=True)
        db.rollback()
        logger.error("DuckDB registration failed: %s", exc)
        raise api_error("DUCKDB_ERROR", f"Failed to register DuckDB view: {exc}", 500)

    response = DatasetResponse(
        dataset_id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        table_name=dataset.table_name,
        original_filename=dataset.original_filename,
        file_extension=dataset.file_extension,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        schema=schema,
        is_active=dataset.is_active,
        upload_timestamp=dataset.upload_timestamp,
    )

    body = response.model_dump(mode="json")
    body["info"] = info
    return JSONResponse(content=body, status_code=201)


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets(db: Session = Depends(get_session)) -> DatasetListResponse:
    datasets = (
        db.query(Dataset).filter(Dataset.is_active == True).all()  # noqa: E712
    )
    items = [
        DatasetResponse(
            dataset_id=ds.id,
            name=ds.name,
            description=ds.description,
            table_name=ds.table_name,
            original_filename=ds.original_filename,
            file_extension=ds.file_extension,
            row_count=ds.row_count,
            column_count=ds.column_count,
            schema=ds.schema_json,
            is_active=ds.is_active,
            upload_timestamp=ds.upload_timestamp,
        )
        for ds in datasets
    ]
    return DatasetListResponse(datasets=items, count=len(items))


@router.delete("/datasets/{dataset_id}")
def delete_dataset(
    dataset_id: str,
    db: Session = Depends(get_session),
) -> dict:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.is_active == True).first()  # noqa: E712
    if dataset is None:
        raise api_error("NOT_FOUND", f"Dataset '{dataset_id}' not found or already inactive", 404)

    dataset.is_active = False

    try:
        svc = get_duckdb_service()
        svc.deregister_dataset(dataset.table_name)
    except Exception as exc:
        logger.warning("DuckDB deregister failed (continuing): %s", exc)

    return {"dataset_id": dataset_id, "is_active": False}
