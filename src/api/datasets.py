"""Dataset routes.

List / detail / preview / delete for uploaded AND derived datasets, plus the
Phase-4 derived-dataset machinery (C25 staleness + `/re-derive`) and the C15
recursive cascade delete.

- `stale` / `derivation_description` are computed for real from lineage
  (`graph.derived.is_stale` / `derivation_description`).
- `POST /datasets/{id}/re-derive` re-runs the stored `derivation_code` against
  the CURRENT parent DataFrames, rewrites the CSV + Parquet + counts, and bumps
  `updated_at` so the dataset is no longer stale.
- `DELETE /datasets/{id}` recursively deletes every derived child whose
  `derived_from_dataset_ids` include the target (transitively), each one's files
  and its query_runs, before deleting the target.
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api._common import ok, api_error
from db.models import ConversationSessionRow, DatasetRow, QueryRunRow
from db.session import get_session
from graph.derived import (
    _columns_json,
    _uploads_dir,
    derivation_description,
    is_stale,
)
from graph.sandbox import build_namespace
from observability.events import get_logger

router = APIRouter()
logger = get_logger("api.datasets")


def _dtype_alias(dtype: str) -> str:
    """Map a pandas dtype string to the spec's stable alias (spec/data.md)."""
    d = dtype.lower()
    if d.startswith("datetime"):
        return "datetime"
    if d.startswith("timedelta"):
        return "duration"
    if d.startswith("bool"):
        return "boolean"
    if d.startswith("category"):
        return "category"
    if d.startswith("int") or d.startswith("uint"):
        return "integer"
    if d.startswith("float"):
        return "float"
    # object / string / anything else -> text
    return "text"


def _columns_schema(columns_json) -> list[dict]:
    """Build `[{name, dtype-alias}]` from the stored columns_json.

    columns_json is `[{name, dtype}]` (as written at upload). Tolerates a bare
    list of names too.
    """
    schema: list[dict] = []
    for entry in columns_json or []:
        if isinstance(entry, dict):
            name = str(entry.get("name", ""))
            dtype = str(entry.get("dtype", "object"))
        else:
            name = str(entry)
            dtype = "object"
        schema.append({"name": name, "dtype": _dtype_alias(dtype)})
    return schema


def _column_names(columns_json) -> list[str]:
    names: list[str] = []
    for entry in columns_json or []:
        names.append(str(entry.get("name", "")) if isinstance(entry, dict) else str(entry))
    return names


def _list_item(row: DatasetRow, session: Session) -> dict:
    return {
        "id": row.id,
        "filename": row.filename,
        "format": row.format,
        "row_count": row.row_count,
        "col_count": row.col_count,
        "columns": _column_names(row.columns_json),
        "origin": row.origin,
        "context": row.context,
        "auto_notes_status": row.auto_notes_status,
        # Real staleness + derivation label from lineage (C25).
        "stale": is_stale(row, session),
        "derived_from_run_id": row.derived_from_run_id,
        "derived_from_dataset_ids": row.derived_from_dataset_ids or [],
        "derivation_description": derivation_description(row),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _format_cell(value):
    """Per-cell formatting for preview: floats round 4, whole floats -> int, NaN -> null."""
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        if value.is_integer():
            return int(value)
        return round(value, 4)
    # numpy scalars surface as python types via .item() upstream; guard anyway
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _load_dataframe(row: DatasetRow) -> pd.DataFrame:
    """Load the dataset's DataFrame (Parquet preferred, CSV fallback)."""
    if row.parquet_path and Path(row.parquet_path).exists():
        return pd.read_parquet(row.parquet_path)
    return pd.read_csv(row.file_path)


def _delete_files(row: DatasetRow) -> None:
    for path_str in (row.file_path, row.parquet_path):
        if not path_str:
            continue
        try:
            Path(path_str).unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("dataset_file_delete_failed", path=path_str, error=str(exc))


@router.get("/datasets")
def list_datasets(session: Session = Depends(get_session)) -> dict:
    rows = session.execute(
        select(DatasetRow).order_by(DatasetRow.created_at.desc())
    ).scalars().all()
    return ok([_list_item(r, session) for r in rows])


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str, session: Session = Depends(get_session)) -> dict:
    row = session.get(DatasetRow, dataset_id)
    if row is None:
        raise api_error("not_found", f"Dataset {dataset_id} not found", 404)
    item = _list_item(row, session)
    item["columns_schema"] = _columns_schema(row.columns_json)
    item["content_hash"] = row.content_hash
    item["file_path"] = row.file_path
    item["parquet_path"] = row.parquet_path
    item["derivation_code"] = row.derivation_code
    item["context_facts"] = row.context_facts or []
    return ok(item)


@router.get("/datasets/{dataset_id}/preview")
def preview_dataset(
    dataset_id: str,
    rows: int = Query(default=10),
    session: Session = Depends(get_session),
) -> dict:
    row = session.get(DatasetRow, dataset_id)
    if row is None:
        raise api_error("not_found", f"Dataset {dataset_id} not found", 404)

    n = max(1, min(50, rows))
    try:
        df = _load_dataframe(row).head(n)
    except Exception as exc:
        logger.error("dataset_preview_read_failed", dataset_id=dataset_id, error=str(exc))
        raise api_error("read_error", f"Could not read dataset: {exc}", 500)

    columns = [str(c) for c in df.columns]
    preview_rows = []
    for record in df.to_dict(orient="records"):
        preview_rows.append({str(k): _format_cell(v) for k, v in record.items()})
    return ok({"columns": columns, "rows": preview_rows})


def _load_parent_frame(parent: DatasetRow) -> pd.DataFrame:
    """Load a parent dataset's DataFrame from the uploads dir (Parquet > CSV).

    Uses `graph.derived._uploads_dir()` (monkeypatchable in tests) so re-derive
    sees the SAME on-disk files the agent wrote. Raises FileNotFoundError when no
    data file is present.
    """
    base = _uploads_dir()
    parquet_path = base / f"{parent.id}.parquet"
    csv_path = base / f"{parent.id}.csv"
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    if csv_path.exists():
        return pd.read_csv(csv_path)
    raise FileNotFoundError(f"No data file for parent dataset {parent.id!r}")


@router.post("/datasets/{dataset_id}/re-derive")
def re_derive_dataset(dataset_id: str, session: Session = Depends(get_session)) -> dict:
    """C25: re-run a derived dataset's `derivation_code` vs its CURRENT parents.

    Rewrites the derived dataset's CSV + Parquet + counts + columns + content
    hash, bumps `updated_at` so it is no longer stale, and returns the updated
    item. Errors: 400 `not_derived` (not a derived dataset / no code), 404
    `parent_not_found` (a parent row or its file is missing), 400 `re_derive_error`
    (the code failed to execute).
    """
    row = session.get(DatasetRow, dataset_id)
    if row is None:
        raise api_error("not_found", f"Dataset {dataset_id} not found", 404)

    if row.origin != "derived" or not (row.derivation_code or "").strip():
        raise api_error(
            "not_derived",
            "This dataset was not derived (no derivation code to re-run).",
            400,
        )

    parent_ids = list(row.derived_from_dataset_ids or [])
    parent_frames: list[pd.DataFrame] = []
    parent_filenames: list[str] = []
    for parent_id in parent_ids:
        parent = session.get(DatasetRow, parent_id)
        if parent is None:
            raise api_error(
                "parent_not_found",
                f"Parent dataset {parent_id} no longer exists.",
                404,
            )
        try:
            parent_frames.append(_load_parent_frame(parent))
        except FileNotFoundError:
            raise api_error(
                "parent_not_found",
                f"Parent dataset {parent_id} has no data file on disk.",
                404,
            )
        parent_filenames.append(parent.filename or f"{parent_id}.csv")

    # Re-run the stored code in the SAME sandbox namespace built over the parents
    # and recover the produced DataFrame object directly (not its stringified
    # transcript form) so we can rewrite the files.
    namespace = build_namespace(parent_frames, parent_filenames)
    try:
        new_df = _eval_to_dataframe(row.derivation_code, namespace)
    except Exception as exc:  # noqa: BLE001 — derivation re-run failure
        raise api_error("re_derive_error", f"Re-derivation failed: {exc}", 400)

    if not isinstance(new_df, pd.DataFrame):
        raise api_error(
            "re_derive_error",
            f"Re-derivation produced {type(new_df).__name__}, not a DataFrame.",
            400,
        )

    base = _uploads_dir()
    base.mkdir(parents=True, exist_ok=True)
    csv_path = base / f"{dataset_id}.csv"
    parquet_path = base / f"{dataset_id}.parquet"
    try:
        new_df.to_csv(csv_path, index=False)
        new_df.to_parquet(parquet_path, index=False)
    except Exception as exc:  # noqa: BLE001 — disk write failure
        raise api_error("re_derive_error", f"Could not write re-derived files: {exc}", 400)

    row.row_count = int(new_df.shape[0])
    row.col_count = int(new_df.shape[1])
    row.columns_json = _columns_json(new_df)
    row.content_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    row.file_path = str(csv_path)
    row.parquet_path = str(parquet_path)
    # Re-derivation IS a new derivation event: bump BOTH created_at (the staleness
    # reference point) and updated_at so the dataset is no longer stale relative to
    # its parents' current updated_at.
    now = _now_aware()
    row.created_at = now
    row.updated_at = now

    item = _list_item(row, session)
    item["stale"] = False
    logger.info("dataset_re_derived", dataset_id=dataset_id, rows=row.row_count)
    return ok(item)


def _eval_to_dataframe(code: str, namespace: dict):
    """Evaluate `code` in the sandbox `namespace` and return the produced object.

    Mirrors `graph.sandbox.eval_expression`'s eval-then-exec fallback but returns
    the actual Python object (a DataFrame for valid derivation code) rather than
    its stringified form. Raises on a syntax/runtime error (caught by the caller).
    """
    code = (code or "").strip()
    if not code:
        raise ValueError("empty derivation code")
    try:
        return eval(code, namespace)  # noqa: S307 — sandboxed, intentional
    except SyntaxError:
        exec(code, namespace)  # noqa: S102 — sandboxed, intentional
        last = code.splitlines()[-1].strip()
        return eval(last, namespace)  # noqa: S307


def _now_aware() -> datetime:
    return datetime.now(timezone.utc)


def _derived_children(session: Session, parent_id: str) -> list[DatasetRow]:
    """Datasets whose `derived_from_dataset_ids` include `parent_id`."""
    children: list[DatasetRow] = []
    candidates = session.execute(
        select(DatasetRow).where(DatasetRow.origin == "derived")
    ).scalars().all()
    for cand in candidates:
        parents = cand.derived_from_dataset_ids or []
        if parent_id in parents:
            children.append(cand)
    return children


def _collect_cascade_ids(session: Session, dataset_id: str) -> list[str]:
    """Ids to delete for a cascade: the target THEN every transitive derived child.

    Returns children-first so files/rows are removed before their parents. Guards
    against cycles via a visited set.
    """
    ordered: list[str] = []
    visited: set[str] = set()

    def _visit(did: str) -> None:
        if did in visited:
            return
        visited.add(did)
        for child in _derived_children(session, did):
            _visit(child.id)
        ordered.append(did)

    _visit(dataset_id)
    return ordered


def _delete_sessions_referencing(session: Session, dataset_id: str) -> int:
    """Delete every conversation session that references `dataset_id` (C15).

    A session references a dataset when its single `dataset_id` column equals the
    id OR when the id appears in its `dataset_ids_json` multi-dataset list. Returns
    the number of session rows removed.
    """
    candidates = session.execute(select(ConversationSessionRow)).scalars().all()
    removed = 0
    for sess in candidates:
        ids = sess.dataset_ids_json or []
        if sess.dataset_id == dataset_id or (
            isinstance(ids, list) and dataset_id in ids
        ):
            session.delete(sess)
            removed += 1
    return removed


def _delete_one(session: Session, dataset_id: str) -> int:
    """Delete a single dataset's files + its query_runs + sessions + the row.

    Returns the number of query_run rows removed. C15 requires the cascade to also
    remove every `conversation_sessions` row that references this dataset (via its
    `dataset_id` column or its `dataset_ids_json` list) so no session is orphaned.

    Fix B (D2): match BOTH the primary dataset_id column AND the dataset_ids_json
    list so multi-dataset runs that reference this dataset as a secondary participant
    are also cleaned up.
    """
    row = session.get(DatasetRow, dataset_id)
    if row is None:
        return 0
    _delete_files(row)
    all_runs = session.execute(select(QueryRunRow)).scalars().all()
    runs_to_delete = [
        r for r in all_runs
        if r.dataset_id == dataset_id
        or dataset_id in (r.dataset_ids_json or [])
    ]
    for r in runs_to_delete:
        session.delete(r)
    _delete_sessions_referencing(session, dataset_id)
    session.delete(row)
    return len(runs_to_delete)


@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: str, session: Session = Depends(get_session)) -> dict:
    row = session.get(DatasetRow, dataset_id)
    if row is None:
        raise api_error("not_found", f"Dataset {dataset_id} not found", 404)

    # Fix A (D1): reject the delete while any run referencing this dataset is
    # still running. A run "references" the dataset via its primary dataset_id
    # column OR via the dataset_ids_json multi-dataset list.
    all_runs = session.execute(select(QueryRunRow)).scalars().all()
    for r in all_runs:
        if r.dataset_id == dataset_id or dataset_id in (r.dataset_ids_json or []):
            if r.status == "running":
                raise api_error(
                    "dataset_in_use",
                    "Dataset is currently being analyzed — retry after the run completes.",
                    409,
                )

    # C15 recursive cascade: delete every transitive derived child first, then
    # the target — each one's files + its query_runs.
    cascade_ids = _collect_cascade_ids(session, dataset_id)
    runs_deleted = 0
    for did in cascade_ids:
        runs_deleted += _delete_one(session, did)

    derived_deleted = [d for d in cascade_ids if d != dataset_id]
    logger.info(
        "dataset_deleted",
        dataset_id=dataset_id,
        runs_deleted=runs_deleted,
        derived_deleted=len(derived_deleted),
    )
    return ok({"deleted": dataset_id, "derived_deleted": derived_deleted})


@router.delete("/datasets")
def delete_all_datasets(session: Session = Depends(get_session)) -> dict:
    rows = session.execute(select(DatasetRow)).scalars().all()
    for row in rows:
        _delete_files(row)
        session.delete(row)
    # Clearing the whole data universe also clears every query_run...
    runs = session.execute(select(QueryRunRow)).scalars().all()
    for r in runs:
        session.delete(r)
    # ...and every conversation session referencing those datasets (C15) — with
    # no datasets left, no session may reference one.
    sessions = session.execute(select(ConversationSessionRow)).scalars().all()
    for s in sessions:
        session.delete(s)
    logger.info(
        "datasets_deleted_all",
        count=len(rows),
        sessions_deleted=len(sessions),
    )
    return ok({"deleted_count": len(rows)})
