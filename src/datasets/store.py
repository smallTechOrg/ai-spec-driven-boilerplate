"""Local dataset store — the privacy boundary in code.

Raw CSV bytes are written to local disk under ``data/datasets/{id}.csv`` and are
NEVER persisted to the database. Only derived metadata (filename, row count) and
the column schema (name + dtype + friendly label, no values) are stored in SQLite.
"""

import json
from pathlib import Path
from uuid import uuid4

import pandas as pd
from sqlalchemy.orm import Session

from config.settings import get_settings
from db.models import DatasetRow
from db.session import create_db_session
from observability.events import get_logger

logger = get_logger("datasets.store")


class DatasetError(Exception):
    """Raised when a dataset cannot be saved/parsed. Carries human-readable copy."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# Friendly dtype mapping: pandas dtype string -> human-facing label.
def _friendly_dtype(dtype: str) -> str:
    d = str(dtype).lower()
    if d.startswith("int"):
        return "integer"
    if d.startswith("uint"):
        return "integer"
    if d.startswith("float"):
        return "decimal"
    if d.startswith("bool"):
        return "boolean"
    if d.startswith("datetime") or d.startswith("date"):
        return "date"
    if d.startswith("timedelta"):
        return "duration"
    if d == "category":
        return "text"
    if d.startswith("object") or d.startswith("string"):
        return "text"
    return "text"


def _data_root() -> Path:
    """Root directory for local dataset storage.

    Resolves to ``<repo root>/data``. Tests override this by monkeypatching
    ``datasets.store._data_root`` to a temp directory.
    """
    # __file__ = src/datasets/store.py -> two parents up = src, three = repo root
    return Path(__file__).resolve().parent.parent.parent / "data"


def _datasets_dir() -> Path:
    return _data_root() / "datasets"


def dataset_path(dataset_id: str) -> Path:
    """Deterministic local path for a dataset's raw CSV."""
    return _datasets_dir() / f"{dataset_id}.csv"


def _build_schema(df: pd.DataFrame) -> list[dict]:
    return [
        {
            "name": str(col),
            "dtype": str(df[col].dtype),
            "friendly_dtype": _friendly_dtype(df[col].dtype),
        }
        for col in df.columns
    ]


def save_dataset(file_bytes: bytes, filename: str) -> DatasetRow:
    """Persist an uploaded CSV locally and record its metadata in SQLite.

    Writes the raw bytes to ``data/datasets/{id}.csv`` (local disk only), parses
    with pandas to derive row count + schema, and stores ONLY metadata + schema in
    the DB. Raw rows never touch the database.

    Raises :class:`DatasetError` with human-readable copy on a bad/oversized/
    unparseable file.
    """
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise DatasetError(
            f"This file is larger than the {settings.max_upload_mb} MB limit. "
            "Please upload a smaller CSV."
        )
    if len(file_bytes) == 0:
        raise DatasetError("This file is empty. Please upload a CSV with data.")

    if filename and not filename.lower().endswith(".csv"):
        raise DatasetError("Only .csv files are supported. Please upload a CSV file.")

    # Parse locally with pandas. Any parse failure becomes human-readable copy.
    from io import BytesIO

    try:
        df = pd.read_csv(BytesIO(file_bytes))
    except Exception as exc:  # noqa: BLE001 - surface as human copy, never a stack trace
        logger.warning("dataset_parse_failed", filename=filename, error=str(exc))
        raise DatasetError(
            "Could not read this file as CSV. Please check the file and try again."
        ) from exc

    if df.shape[1] == 0 or df.shape[0] == 0:
        raise DatasetError(
            "This CSV has no data rows or columns. Please upload a populated CSV."
        )

    dataset_id = str(uuid4())
    schema = _build_schema(df)
    row_count = int(len(df))

    # Write raw bytes to local disk only.
    target = dataset_path(dataset_id)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(file_bytes)
    except OSError as exc:
        logger.error("dataset_write_failed", dataset_id=dataset_id, error=str(exc))
        raise DatasetError(
            "Could not save the uploaded file to local storage. Please try again."
        ) from exc

    # Persist metadata + schema ONLY (never raw rows) to SQLite.
    try:
        with create_db_session() as session:
            row = DatasetRow(
                id=dataset_id,
                filename=filename or f"{dataset_id}.csv",
                row_count=row_count,
                schema_json=json.dumps(schema),
            )
            session.add(row)
            session.flush()
            session.expunge(row)
    except Exception as exc:  # noqa: BLE001
        # Roll back the local file so we don't leave an orphaned raw CSV.
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        logger.error("dataset_db_insert_failed", dataset_id=dataset_id, error=str(exc))
        raise DatasetError(
            "Could not record the dataset. Please try again."
        ) from exc

    logger.info(
        "dataset_uploaded",
        dataset_id=dataset_id,
        row_count=row_count,
        n_columns=len(schema),
    )
    return row


def get_dataset(session: Session, dataset_id: str) -> DatasetRow | None:
    """Fetch dataset metadata from SQLite, or ``None`` if not found."""
    return session.get(DatasetRow, dataset_id)
