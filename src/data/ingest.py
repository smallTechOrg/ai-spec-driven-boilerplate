"""Ingestion — load an uploaded CSV or Excel file into the local DuckDB engine.

CSV is read directly by DuckDB (`read_csv_auto`) for speed on large files.
Each Excel SHEET becomes its own dataset: it is parsed with pandas/openpyxl and
materialised to a local parquet cache the DuckDB engine reads back. Returns one
`IngestedDataset` per sheet (one for CSV). Raw data stays on the local disk.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from data.duckdb_engine import DEFAULT_TABLE, DatasetRef, _sql_str
from data.profiler import profile_connection

# Default ~100 MB upload cap.
MAX_FILE_BYTES = 100 * 1024 * 1024

_CSV_EXTS = {".csv"}
_EXCEL_EXTS = {".xlsx"}


class IngestError(Exception):
    """Raised for unsupported / empty / unparseable uploads (maps to 400)."""


class FileTooLargeError(IngestError):
    """Raised when the upload exceeds the configured cap (maps to 413)."""


@dataclass
class IngestedDataset:
    """A single loaded dataset (one CSV, or one Excel sheet)."""

    id: str
    name: str
    source_path: str
    source_kind: str            # "csv" | "excel"
    sheet_name: str | None
    duckdb_table: str
    profile: dict[str, Any]
    row_count: int
    size_bytes: int

    def ref(self) -> DatasetRef:
        return DatasetRef(
            dataset_id=self.id,
            source_path=self.source_path,
            source_kind=self.source_kind,
            duckdb_table=self.duckdb_table,
            sheet_name=self.sheet_name,
        )


def _safe_stem(name: str) -> str:
    stem = Path(name).stem
    cleaned = re.sub(r"[^0-9a-zA-Z_]+", "_", stem).strip("_")
    return cleaned or "dataset"


def ingest_file(
    *,
    filename: str,
    content: bytes,
    storage_dir: str | Path,
    max_bytes: int = MAX_FILE_BYTES,
) -> list[IngestedDataset]:
    """Persist the upload to `storage_dir`, load it into DuckDB, and profile it.

    Returns one IngestedDataset per sheet (Excel) or a single entry (CSV).
    Raises IngestError (400) on unsupported/empty/unparseable input and
    FileTooLargeError (413) when the size cap is exceeded.
    """
    if not content:
        raise IngestError("The uploaded file is empty.")
    if len(content) > max_bytes:
        raise FileTooLargeError(
            f"File exceeds the maximum size of {max_bytes // (1024 * 1024)} MB."
        )

    ext = Path(filename).suffix.lower()
    storage = Path(storage_dir)
    storage.mkdir(parents=True, exist_ok=True)
    size_bytes = len(content)

    if ext in _CSV_EXTS:
        return [_ingest_csv(filename, content, storage, size_bytes)]
    if ext in _EXCEL_EXTS:
        return _ingest_excel(filename, content, storage, size_bytes)
    raise IngestError(
        f"Unsupported file type {ext!r}. Only .csv and .xlsx are accepted."
    )


def _ingest_csv(
    filename: str, content: bytes, storage: Path, size_bytes: int
) -> IngestedDataset:
    dataset_id = str(uuid.uuid4())
    stored = storage / f"{dataset_id}.csv"
    stored.write_bytes(content)

    ref = DatasetRef(
        dataset_id=dataset_id,
        source_path=str(stored),
        source_kind="csv",
        duckdb_table=DEFAULT_TABLE,
    )
    conn = duckdb.connect(database=":memory:")
    try:
        try:
            conn.execute(
                f"CREATE OR REPLACE VIEW {DEFAULT_TABLE} AS "
                f"SELECT * FROM read_csv_auto({_sql_str(stored)}, header=true)"
            )
            profile = profile_connection(conn)
        except Exception as exc:
            raise IngestError(f"Could not parse the CSV file: {exc}") from exc
    finally:
        conn.close()

    if profile["row_count"] == 0:
        raise IngestError("The CSV file contains no data rows.")

    return IngestedDataset(
        id=dataset_id,
        name=Path(filename).name,
        source_path=str(stored),
        source_kind="csv",
        sheet_name=None,
        duckdb_table=DEFAULT_TABLE,
        profile=profile,
        row_count=profile["row_count"],
        size_bytes=size_bytes,
    )


def _ingest_excel(
    filename: str, content: bytes, storage: Path, size_bytes: int
) -> list[IngestedDataset]:
    raw_path = storage / f"{uuid.uuid4()}_{_safe_stem(filename)}.xlsx"
    raw_path.write_bytes(content)

    try:
        sheets = pd.read_excel(raw_path, sheet_name=None, engine="openpyxl")
    except Exception as exc:
        raise IngestError(f"Could not parse the Excel file: {exc}") from exc

    if not sheets:
        raise IngestError("The Excel file contains no sheets.")

    datasets: list[IngestedDataset] = []
    for sheet_name, frame in sheets.items():
        if frame is None or frame.empty:
            continue
        dataset_id = str(uuid.uuid4())
        cache = storage / f"{dataset_id}.parquet"

        conn = duckdb.connect(database=":memory:")
        try:
            # Materialise the sheet to a local parquet cache via DuckDB (native
            # parquet — no pyarrow needed), then load + profile it.
            sheet_frame = frame  # referenced by DuckDB's pandas scan
            conn.register("sheet_frame", sheet_frame)
            try:
                conn.execute(
                    f"COPY (SELECT * FROM sheet_frame) TO {_sql_str(cache)} "
                    "(FORMAT PARQUET)"
                )
            except Exception as exc:
                raise IngestError(
                    f"Could not load sheet {sheet_name!r}: {exc}"
                ) from exc
            conn.execute(
                f"CREATE OR REPLACE VIEW {DEFAULT_TABLE} AS "
                f"SELECT * FROM read_parquet({_sql_str(cache)})"
            )
            profile = profile_connection(conn)
        finally:
            conn.close()

        datasets.append(
            IngestedDataset(
                id=dataset_id,
                name=f"{Path(filename).name} — {sheet_name}",
                source_path=str(cache),
                source_kind="excel",
                sheet_name=sheet_name,
                duckdb_table=DEFAULT_TABLE,
                profile=profile,
                row_count=profile["row_count"],
                size_bytes=size_bytes,
            )
        )

    if not datasets:
        raise IngestError("The Excel file has no non-empty sheets.")
    return datasets
