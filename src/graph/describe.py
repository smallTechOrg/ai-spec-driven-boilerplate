"""C30 on-demand dataset notes generation (`generate_dataset_notes`).

`spec/agent.md` -> "## Graph-adjacent single LLM calls": sample up to 50 rows of a
dataset, make ONE `LLMClient` call with `describe.md` for <= 300-word plain notes,
write them to `datasets.context`, and track `datasets.auto_notes_status`
(pending -> done / failed). On success, trigger C31 fact extraction
(`graph.compress.extract_facts`).

This runs both on upload (async, fire-and-forget) and on `POST /datasets/{id}/describe`.
A generation failure sets `auto_notes_status="failed"` and NEVER crashes — the
upload / route that triggered it must not be affected.

All LLM calls go through `LLMClient` (never a provider SDK directly).
"""
from __future__ import annotations

import threading
from pathlib import Path

import pandas as pd

from db.models import DatasetRow
from db.session import create_db_session
from graph.compress import extract_facts
from llm.client import LLMClient
from observability.events import get_logger

logger = get_logger("graph.describe")

# Sample size for the notes prompt (spec: "sample 50 rows").
_SAMPLE_ROWS = 50

# Hard cap on the stored notes (spec/data.md: context <= 4000 chars).
_CONTEXT_MAX = 4000

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_DESCRIBE_PROMPT_PATH = _PROMPTS_DIR / "describe.md"

# Node tag so the stub provider can branch deterministically. The stub has no
# `<node:describe>` branch, so OFFLINE the reply is a stub fallback string; this
# helper still completes (status "done") but with placeholder text. The
# authoritative gate is real Gemini, which returns real prose.
_DESCRIBE_TAG = "<node:describe>"


def _load_dataframe(row: DatasetRow) -> pd.DataFrame:
    """Load the dataset's DataFrame (Parquet preferred, CSV fallback).

    Mirrors `api.datasets._load_dataframe` — kept local so this module owns its
    own file access without importing across the api/graph boundary.
    """
    if row.parquet_path and Path(row.parquet_path).exists():
        return pd.read_parquet(row.parquet_path)
    return pd.read_csv(row.file_path)


def _build_describe_prompt(row: DatasetRow, df: pd.DataFrame) -> str:
    """Assemble the user prompt: filename + column schema + a row sample."""
    sample = df.head(_SAMPLE_ROWS)
    cols = ", ".join(f"{c} ({df[c].dtype})" for c in df.columns)
    try:
        sample_text = sample.to_string(index=False, max_rows=_SAMPLE_ROWS)
    except Exception:  # noqa: BLE001 — never let formatting break notes
        sample_text = sample.to_string()
    return (
        f"{_DESCRIBE_TAG}\n\n"
        f"## Dataset\n"
        f"Filename: {row.filename}\n"
        f"Rows: {df.shape[0]}, Columns: {df.shape[1]}\n\n"
        f"## Column schema\n{cols}\n\n"
        f"## Sample rows (first {min(_SAMPLE_ROWS, df.shape[0])})\n{sample_text}\n\n"
        "Write the plain-language notes for this dataset (at most 300 words)."
    )


def _set_status(dataset_id: str, status: str, context: str | None = None) -> None:
    """Update `auto_notes_status` (and optionally `context`) for a dataset.

    Best-effort: a DB error here is logged, never raised.
    """
    try:
        with create_db_session() as session:
            row = session.get(DatasetRow, dataset_id)
            if row is None:
                return
            row.auto_notes_status = status
            if context is not None:
                row.context = context[:_CONTEXT_MAX]
    except Exception as exc:  # noqa: BLE001 — status write must not crash
        logger.warning("describe_status_write_failed", dataset_id=dataset_id, error=str(exc))


def generate_dataset_notes(dataset_id: str) -> str:
    """C30 sync core: generate notes for a dataset and persist them.

    Sets `auto_notes_status="pending"`, samples <= 50 rows, makes ONE LLM call,
    writes the notes to `context` and sets `done`; on ANY failure sets `failed`
    and returns "". On success triggers C31 (`extract_facts`). NEVER raises.
    """
    # 1) Load the row + DataFrame.
    try:
        with create_db_session() as session:
            row = session.get(DatasetRow, dataset_id)
            if row is None:
                logger.warning("describe_dataset_missing", dataset_id=dataset_id)
                return ""
            # Snapshot the row fields we need outside the session.
            row_snapshot = DatasetRow(
                id=row.id,
                filename=row.filename,
                file_path=row.file_path,
                parquet_path=row.parquet_path,
                row_count=row.row_count,
                col_count=row.col_count,
                columns_json=row.columns_json,
                content_hash=row.content_hash,
                format=row.format,
                origin=row.origin,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("describe_load_row_failed", dataset_id=dataset_id, error=str(exc))
        _set_status(dataset_id, "failed")
        return ""

    _set_status(dataset_id, "pending")

    try:
        df = _load_dataframe(row_snapshot)
    except Exception as exc:  # noqa: BLE001 — unreadable file -> failed, not crash
        logger.warning("describe_read_df_failed", dataset_id=dataset_id, error=str(exc))
        _set_status(dataset_id, "failed")
        return ""

    # 2) One LLM call for the notes.
    try:
        system = _DESCRIBE_PROMPT_PATH.read_text(encoding="utf-8").strip()
        prompt = _build_describe_prompt(row_snapshot, df)
        notes = (LLMClient().call_model(prompt, system=system) or "").strip()
    except Exception as exc:  # noqa: BLE001 — LLM failure -> failed status
        logger.warning("describe_llm_failed", dataset_id=dataset_id, error=str(exc))
        _set_status(dataset_id, "failed")
        return ""

    if not notes:
        logger.warning("describe_empty_notes", dataset_id=dataset_id)
        _set_status(dataset_id, "failed")
        return ""

    # 3) Persist notes + done status.
    _set_status(dataset_id, "done", context=notes)
    logger.info("describe_done", dataset_id=dataset_id, notes_len=len(notes))

    # 4) Trigger C31 fact extraction (best-effort — failure leaves facts []).
    try:
        extract_facts(dataset_id)
    except Exception as exc:  # noqa: BLE001 — compression is non-fatal
        logger.warning("describe_trigger_compress_failed", dataset_id=dataset_id, error=str(exc))

    return notes[:_CONTEXT_MAX]


def trigger_describe_async(dataset_id: str) -> threading.Thread:
    """Fire-and-forget C30 in a daemon thread; returns the started thread.

    Suitable for calling from the upload route and the `/describe` route — it must
    never block or fail the caller. The thread runs `generate_dataset_notes`,
    which itself never raises.
    """

    def _run() -> None:
        try:
            generate_dataset_notes(dataset_id)
        except Exception as exc:  # noqa: BLE001 — belt-and-braces; core never raises
            logger.warning("trigger_describe_async_failed", dataset_id=dataset_id, error=str(exc))

    thread = threading.Thread(
        target=_run, name=f"describe-{dataset_id[:8]}", daemon=True
    )
    thread.start()
    return thread
