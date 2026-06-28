"""Phase-1 dataset routes: upload+profile, and ask (SSE step stream + answer).

``POST /datasets``        — multipart upload, local profile, persist Dataset.
``POST /datasets/{id}/ask`` — run the graph; stream live step events over SSE,
                              then a final event carrying the answer envelope.

SSE streaming model (producer/consumer):
  - The graph runs in a worker thread (``run_ask`` is sync + blocking on the LLM).
  - Its ``on_step(step, status)`` callback drops ``{"step","status"}`` events onto
    a thread-safe ``queue.Queue``.
  - The async StreamingResponse generator drains that queue in a loop, yielding
    each step as an SSE ``data:`` frame the moment it arrives — so steps stream
    LIVE, not batched at the end.
  - When the worker finishes it enqueues a sentinel carrying the final result
    (or an error); the generator emits the final envelope frame and stops.
"""

from __future__ import annotations

import json
import queue
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from analysis.profiler import profile_csv
from api._common import api_error, ok
from db.models import Dataset
from db.session import create_db_session
from domain.dataset import AskRequest
from graph.runner import DatasetNotFound, run_ask

router = APIRouter()

# Raw files live on disk (privacy boundary); the DB stores only metadata.
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "uploads"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # ~100MB (spec key constraint)

_SENTINEL = object()


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/datasets")
async def upload_dataset(file: UploadFile = File(...)) -> dict:
    """Accept a CSV upload, profile it locally over ALL rows, persist a Dataset."""
    raw = await file.read()
    if not raw:
        raise api_error("EMPTY_FILE", "Uploaded file is empty.", 400)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise api_error(
            "FILE_TOO_LARGE",
            f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit.",
            400,
        )

    original_name = file.filename or "dataset.csv"
    safe_name = Path(original_name).name
    stored_path = UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe_name}"

    # --- Storage (500 on failure) ---
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        stored_path.write_bytes(raw)
    except OSError as exc:
        raise api_error("STORAGE_FAILURE", f"Could not store file: {exc}", 500)

    # --- Local profile (400 on unparseable) ---
    try:
        profiled = await run_in_threadpool(profile_csv, str(stored_path))
    except ValueError as exc:
        stored_path.unlink(missing_ok=True)
        raise api_error("UNPARSEABLE_FILE", str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        stored_path.unlink(missing_ok=True)
        raise api_error("PROFILE_FAILURE", f"Could not profile file: {exc}", 400)

    with create_db_session() as session:
        dataset = Dataset(
            name=safe_name,
            file_path=str(stored_path),
            source_kind="csv",
            row_count=profiled["row_count"],
            column_count=profiled["column_count"],
            profile=profiled["profile"],
            sample_rows=profiled["sample_rows"],
        )
        session.add(dataset)
        session.flush()
        dataset_id = dataset.id

    return ok(
        {
            "dataset_id": dataset_id,
            "name": safe_name,
            "row_count": profiled["row_count"],
            "column_count": profiled["column_count"],
            "profile": profiled["profile"],
            "sample_rows": profiled["sample_rows"],
        }
    )


@router.post("/datasets/{dataset_id}/ask")
async def ask(dataset_id: str, body: AskRequest, request: Request):
    """Run one analysis turn; stream step events, then the final answer envelope."""
    question = (body.question or "").strip()
    if not question:
        raise api_error("MISSING_QUESTION", "A question is required.", 422)

    # Fail fast on an unknown dataset BEFORE opening the stream (clean 404).
    with create_db_session() as session:
        if session.get(Dataset, dataset_id) is None:
            raise api_error("DATASET_NOT_FOUND", f"Dataset {dataset_id} not found.", 404)

    events: queue.Queue = queue.Queue()

    def _on_step(step: str, status: str) -> None:
        events.put({"step": step, "status": status})

    def _worker() -> None:
        try:
            data = run_ask(dataset_id, body.conversation_id, question, _on_step)
            events.put((_SENTINEL, ok(data)))
        except DatasetNotFound:
            events.put(
                (
                    _SENTINEL,
                    {
                        "data": None,
                        "error": {
                            "code": "DATASET_NOT_FOUND",
                            "message": f"Dataset {dataset_id} not found.",
                        },
                    },
                )
            )
        except Exception as exc:  # noqa: BLE001 — surface a clean error frame
            events.put(
                (
                    _SENTINEL,
                    {
                        "data": None,
                        "error": {"code": "GRAPH_FAILURE", "message": str(exc)},
                    },
                )
            )

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()

    async def _stream():
        while True:
            try:
                item = await run_in_threadpool(events.get, True, 0.25)
            except queue.Empty:
                continue
            if isinstance(item, tuple) and item and item[0] is _SENTINEL:
                yield _sse(item[1])
                break
            yield _sse(item)

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
