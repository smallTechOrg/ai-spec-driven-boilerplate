"""Dataset operations routes (Phase 4, slice-4b).

Kept SEPARATE from `api.datasets` (Phase-2 list/detail/preview/delete) so the two
slices never collide on one file. This module owns the mutating / LLM-backed
dataset operations:

- `POST  /datasets/{id}/clean`        — C24 NL cleaning PREVIEW (run on a copy)
- `POST  /datasets/{id}/clean/apply`  — C24 apply in place (rewrite CSV + Parquet)
- `POST  /datasets/{id}/describe`     — C30 trigger (async notes generation)
- `PATCH /datasets/{id}/context`      — set the user/auto notes (<= 4000 chars)

Envelopes (`ok` / `api_error`), the session dependency (`get_session`), and the
DataFrame loader mirror `api.datasets` exactly — small local copies keep file
ownership clean. All LLM work goes through `LLMClient` via `clean.md` (preview /
apply) and via `graph.describe` (notes); never a provider SDK directly.
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api._common import ok, api_error
from db.models import DatasetRow
from db.session import get_session
from graph.describe import trigger_describe_async
from graph.sandbox import build_namespace
from llm.client import LLMClient
from observability.events import get_logger

router = APIRouter()
logger = get_logger("api.datasets_ops")

_CONTEXT_MAX = 4000  # spec/data.md: dataset context <= 4000 chars
_PREVIEW_ROWS = 10  # rows returned in clean preview_before / preview_after

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_CLEAN_PROMPT_PATH = _PROMPTS_DIR / "clean.md"


# --------------------------------------------------------------------------- #
# Local helpers (mirror api.datasets — kept local to avoid cross-module imports)
# --------------------------------------------------------------------------- #


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_dataframe(row: DatasetRow) -> pd.DataFrame:
    """Load the dataset's DataFrame (Parquet preferred, CSV fallback)."""
    if row.parquet_path and Path(row.parquet_path).exists():
        return pd.read_parquet(row.parquet_path)
    return pd.read_csv(row.file_path)


def _format_cell(value):
    """Per-cell formatting: floats round 4, whole floats -> int, NaN -> null."""
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        if value.is_integer():
            return int(value)
        return round(value, 4)
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _preview_rows(df: pd.DataFrame, n: int = _PREVIEW_ROWS) -> list[dict]:
    rows: list[dict] = []
    for record in df.head(n).to_dict(orient="records"):
        rows.append({str(k): _format_cell(v) for k, v in record.items()})
    return rows


def _columns_json(df: pd.DataFrame) -> list[dict]:
    return [{"name": str(c), "dtype": str(df[c].dtype)} for c in df.columns]


def _schema_lines(df: pd.DataFrame) -> str:
    return ", ".join(f"{c} ({df[c].dtype})" for c in df.columns)


def _summary(row: DatasetRow) -> dict:
    """Compact updated-dataset summary returned by clean/apply."""
    return {
        "id": row.id,
        "filename": row.filename,
        "format": row.format,
        "row_count": row.row_count,
        "col_count": row.col_count,
        "columns": [str(c.get("name")) if isinstance(c, dict) else str(c)
                    for c in (row.columns_json or [])],
        "origin": row.origin,
        "context": row.context,
        "auto_notes_status": row.auto_notes_status,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _generate_clean_code(df: pd.DataFrame, instruction: str) -> str:
    """ONE LLM call: schema + instruction -> a single pandas expression string."""
    system = _CLEAN_PROMPT_PATH.read_text(encoding="utf-8").strip()
    prompt = (
        "## Column schema\n"
        f"{_schema_lines(df)}\n\n"
        "## Cleaning instruction\n"
        f"{instruction.strip()}\n\n"
        "Output ONLY the single pandas expression (transforming `df`)."
    )
    reply = LLMClient().call_model(prompt, system=system)
    return _strip_code_fences((reply or "").strip())


def _strip_code_fences(text: str) -> str:
    """Remove a ```...``` fence the model may add despite instructions."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        # drop opening fence (``` or ```python)
        lines = lines[1:]
        # drop closing fence if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def _run_clean(df: pd.DataFrame, code: str, filename: str) -> pd.DataFrame:
    """Execute `code` against a COPY of `df` in the sandbox; return the result.

    The cleaning code is a single pandas EXPRESSION (per `clean.md`) whose value is
    the cleaned DataFrame, evaluated ONCE in the sandbox namespace built from a copy
    of `df` (the stored file is never mutated). Raises ValueError on an exec error
    OR a non-DataFrame result (the caller maps this to a 422 `clean_error`).
    """
    work = df.copy()
    namespace = build_namespace([work], [filename])
    try:
        obj = eval(code, namespace)  # noqa: S307 — sandboxed clean expression
    except SyntaxError:
        # Statement form (e.g. an assignment): exec, then fall back to the `df`
        # binding mutated in the namespace as the cleaned frame.
        try:
            exec(code, namespace)  # noqa: S102 — sandboxed, intentional
        except Exception as exc:  # noqa: BLE001 — recoverable -> 422
            raise ValueError(f"{type(exc).__name__}: {exc}")
        obj = namespace.get("df")
    except Exception as exc:  # noqa: BLE001 — recoverable exec error -> 422
        raise ValueError(f"{type(exc).__name__}: {exc}")

    if not isinstance(obj, pd.DataFrame):
        raise ValueError(
            f"cleaning code must produce a DataFrame, got {type(obj).__name__}"
        )
    return obj


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #


class CleanBody(BaseModel):
    instruction: str | None = None
    code: str | None = None


class ContextBody(BaseModel):
    context: str | None = None


# --------------------------------------------------------------------------- #
# POST /datasets/{id}/clean  — C24 PREVIEW
# --------------------------------------------------------------------------- #


@router.post("/datasets/{dataset_id}/clean")
def clean_preview(
    dataset_id: str,
    body: CleanBody,
    session: Session = Depends(get_session),
) -> dict:
    row = session.get(DatasetRow, dataset_id)
    if row is None:
        raise api_error("not_found", f"Dataset {dataset_id} not found", 404)

    instruction = (body.instruction or "").strip()
    if not instruction:
        raise api_error("invalid_body", "`instruction` is required.", 400)

    try:
        df = _load_dataframe(row)
    except Exception as exc:  # noqa: BLE001
        logger.error("clean_read_failed", dataset_id=dataset_id, error=str(exc))
        raise api_error("read_error", f"Could not read dataset: {exc}", 500)

    code = _generate_clean_code(df, instruction)
    if not code:
        raise api_error("clean_error", "Model returned no cleaning code.", 422)

    try:
        cleaned = _run_clean(df, code, row.filename)
    except ValueError as exc:
        logger.info("clean_exec_error", dataset_id=dataset_id, error=str(exc))
        raise api_error("clean_error", f"Cleaning code failed: {exc}", 422)

    before = {"rows": int(df.shape[0]), "cols": int(df.shape[1])}
    after = {"rows": int(cleaned.shape[0]), "cols": int(cleaned.shape[1])}
    logger.info(
        "clean_preview_ok", dataset_id=dataset_id,
        before=before, after=after,
    )
    return ok(
        {
            "code": code,
            "before": before,
            "after": after,
            "preview_before": _preview_rows(df),
            "preview_after": _preview_rows(cleaned),
        }
    )


# --------------------------------------------------------------------------- #
# POST /datasets/{id}/clean/apply  — C24 APPLY in place
# --------------------------------------------------------------------------- #


@router.post("/datasets/{dataset_id}/clean/apply")
def clean_apply(
    dataset_id: str,
    body: CleanBody,
    session: Session = Depends(get_session),
) -> dict:
    row = session.get(DatasetRow, dataset_id)
    if row is None:
        raise api_error("not_found", f"Dataset {dataset_id} not found", 404)

    try:
        df = _load_dataframe(row)
    except Exception as exc:  # noqa: BLE001
        logger.error("clean_apply_read_failed", dataset_id=dataset_id, error=str(exc))
        raise api_error("read_error", f"Could not read dataset: {exc}", 500)

    # Use the previewed `code` if provided; else regenerate from `instruction`.
    code = _strip_code_fences((body.code or "").strip())
    if not code:
        instruction = (body.instruction or "").strip()
        if not instruction:
            raise api_error(
                "invalid_body", "`code` or `instruction` is required.", 400
            )
        code = _generate_clean_code(df, instruction)
    if not code:
        raise api_error("clean_error", "No cleaning code to apply.", 422)

    try:
        cleaned = _run_clean(df, code, row.filename)
    except ValueError as exc:
        logger.info("clean_apply_exec_error", dataset_id=dataset_id, error=str(exc))
        raise api_error("clean_error", f"Cleaning code failed: {exc}", 422)

    # Rewrite the on-disk files in place (CSV + Parquet).
    csv_path = Path(row.file_path) if row.file_path else None
    parquet_path = Path(row.parquet_path) if row.parquet_path else None
    try:
        if csv_path is not None:
            cleaned.to_csv(csv_path, index=False)
        if parquet_path is not None:
            cleaned.to_parquet(parquet_path, index=False)
    except Exception as exc:  # noqa: BLE001
        logger.error("clean_apply_write_failed", dataset_id=dataset_id, error=str(exc))
        raise api_error("write_failed", f"Failed to rewrite dataset: {exc}", 500)

    # Update metadata. Bump updated_at so derived children become stale (slice-4a
    # computes staleness from parent.updated_at > child.created_at).
    row.row_count = int(cleaned.shape[0])
    row.col_count = int(cleaned.shape[1])
    row.columns_json = _columns_json(cleaned)
    if csv_path is not None and csv_path.exists():
        row.content_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    row.updated_at = _now()

    logger.info(
        "clean_apply_ok", dataset_id=dataset_id,
        rows=row.row_count, cols=row.col_count,
    )
    return ok(_summary(row))


# --------------------------------------------------------------------------- #
# POST /datasets/{id}/describe  — C30 trigger
# --------------------------------------------------------------------------- #


@router.post("/datasets/{dataset_id}/describe")
def describe_dataset(
    dataset_id: str,
    session: Session = Depends(get_session),
) -> dict:
    row = session.get(DatasetRow, dataset_id)
    if row is None:
        raise api_error("not_found", f"Dataset {dataset_id} not found", 404)

    # Mark pending synchronously so the very next GET reflects the in-progress
    # state, then fire the async notes job (fire-and-forget; never blocks).
    row.auto_notes_status = "pending"
    session.flush()
    trigger_describe_async(dataset_id)

    logger.info("describe_triggered", dataset_id=dataset_id)
    return ok({"dataset_id": dataset_id, "auto_notes_status": "pending"})


# --------------------------------------------------------------------------- #
# PATCH /datasets/{id}/context  — set user/auto notes (<= 4000 chars)
# --------------------------------------------------------------------------- #


@router.patch("/datasets/{dataset_id}/context")
def patch_context(
    dataset_id: str,
    body: ContextBody,
    session: Session = Depends(get_session),
) -> dict:
    row = session.get(DatasetRow, dataset_id)
    if row is None:
        raise api_error("not_found", f"Dataset {dataset_id} not found", 404)

    context = body.context or ""
    if len(context) > _CONTEXT_MAX:
        raise api_error(
            "context_too_long",
            f"Context must be at most {_CONTEXT_MAX} characters (got {len(context)}).",
            400,
        )

    row.context = context if context else None
    row.updated_at = _now()
    logger.info("context_updated", dataset_id=dataset_id, length=len(context))
    return ok(
        {
            "id": row.id,
            "context": row.context,
            "auto_notes_status": row.auto_notes_status,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
    )
