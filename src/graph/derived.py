"""Derived-dataset registration, lineage, staleness, and re-derivation (C25).

The agent can autonomously materialise a new dataset via the sandbox tool
`save_dataset(df, name, desc)`. This module owns the *deterministic* machinery
behind it (no LLM): it writes the on-disk CSV + Parquet, inserts a `datasets`
row with full lineage (`origin="derived"`, `derived_from_run_id`,
`derived_from_dataset_ids`, `derivation_code`), computes staleness, and re-runs
the derivation code against the current parent DataFrames.

Per `spec/data.md`:
- Files live at `uploads/{dataset_id}.csv` (+ `.parquet`).
- A derived dataset is STALE when any parent's `updated_at` is later than the
  derived dataset's `created_at` (a parent changed after derivation).

`_uploads_dir()` resolves the repo-root `uploads/` and is monkeypatched in tests
(mirroring `graph.nodes._uploads_dir` / `graph.runner._uploads_dir`).
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from db.models import DatasetRow
from db.session import create_db_session
from observability.events import get_logger

logger = get_logger("graph.derived")

_SANITISE_RE = re.compile(r"[^0-9A-Za-z._-]+")


def _uploads_dir() -> Path:
    """`uploads/` at the repo root (two levels up from src/graph/).

    Monkeypatched in tests to a tmp dir, consistent with nodes/runner.
    """
    return Path(__file__).resolve().parent.parent.parent / "uploads"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sanitise_name(name: str) -> str:
    """Turn an arbitrary save_dataset `name` into a reasonable display filename.

    Strips path separators / odd characters, ensures a `.csv` suffix, and falls
    back to a default when empty.
    """
    stem = (name or "").strip()
    # Drop any path components a model might pass.
    stem = stem.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    # Drop a trailing extension so we can normalise to .csv.
    if "." in stem:
        stem = stem.rsplit(".", 1)[0]
    stem = _SANITISE_RE.sub("_", stem).strip("_")
    if not stem:
        stem = "derived_dataset"
    return f"{stem}.csv"


def _columns_json(df: pd.DataFrame) -> list[dict]:
    return [{"name": str(c), "dtype": str(df[c].dtype)} for c in df.columns]


def register_derived_dataset(
    df: pd.DataFrame,
    name: str,
    desc: str = "",
    *,
    run_id: str | None,
    parent_ids: list[str],
    derivation_code: str,
) -> str:
    """Persist `df` as a registered DERIVED dataset and return its new id.

    Writes `uploads/{id}.csv` + `.parquet`, inserts a `DatasetRow` with
    `origin="derived"` and full lineage. Raises on disk/db failure (the caller —
    `save_dataset`'s closure — catches it and records a step error).
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"save_dataset expects a pandas DataFrame, got {type(df).__name__}"
        )

    display_name = _sanitise_name(name)
    columns_json = _columns_json(df)

    base = _uploads_dir()
    base.mkdir(parents=True, exist_ok=True)

    with create_db_session() as session:
        row = DatasetRow(
            filename=display_name,
            file_path="",  # set below once id is known
            row_count=int(df.shape[0]),
            col_count=int(df.shape[1]),
            columns_json=columns_json,
            content_hash="",  # set below from the written CSV bytes
            format="csv",
            context=(desc or None),
            origin="derived",
            derived_from_run_id=run_id,
            derived_from_dataset_ids=list(parent_ids or []),
            derivation_code=derivation_code or "",
        )
        session.add(row)
        session.flush()  # assigns row.id
        dataset_id = row.id

        csv_path = base / f"{dataset_id}.csv"
        parquet_path = base / f"{dataset_id}.parquet"
        df.to_csv(csv_path, index=False)
        df.to_parquet(parquet_path, index=False)

        content_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        row.file_path = str(csv_path)
        row.parquet_path = str(parquet_path)
        row.content_hash = content_hash

    logger.info(
        "derived_dataset_registered",
        dataset_id=dataset_id,
        run_id=run_id,
        parents=list(parent_ids or []),
        rows=int(df.shape[0]),
        cols=int(df.shape[1]),
    )
    return dataset_id


def is_stale(row: DatasetRow, session) -> bool:
    """A derived dataset is stale when any parent changed after derivation.

    Stale ⇔ some parent's `updated_at` > this row's `created_at`. Non-derived
    datasets are never stale. Missing parents do not by themselves mark stale
    here (that is surfaced via re-derive 404); a missing parent yields False.
    """
    if row.origin != "derived":
        return False
    parent_ids = row.derived_from_dataset_ids or []
    if not parent_ids:
        return False
    derived_at = row.created_at
    if derived_at is None:
        return False
    for parent_id in parent_ids:
        parent = session.get(DatasetRow, parent_id)
        if parent is None or parent.updated_at is None:
            continue
        if _as_aware(parent.updated_at) > _as_aware(derived_at):
            return True
    return False


def _as_aware(value: datetime) -> datetime:
    """Treat naive timestamps as UTC so comparisons never raise (SQLite quirk)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def derivation_description(row: DatasetRow) -> str | None:
    """A short human label for a derived dataset.

    Prefers the user/auto note (`context`), falling back to the first line of the
    derivation code. None for non-derived datasets.
    """
    if row.origin != "derived":
        return None
    note = (row.context or "").strip()
    if note:
        first = note.splitlines()[0].strip()
        return first[:200]
    code = (row.derivation_code or "").strip()
    if code:
        return code.splitlines()[0].strip()[:200]
    return None
