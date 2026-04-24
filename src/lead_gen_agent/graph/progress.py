"""In-memory progress event registry for SSE observability.

Each run_id maps to an asyncio.Queue. Pipeline nodes call emit() (which is
thread-safe) to push progress messages. The SSE route consumes the queue.
A None sentinel signals the end of the stream.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

# run_id → Queue of {"step": str, "message": str} dicts (None = done sentinel)
_registry: dict[str, asyncio.Queue] = {}

# The main asyncio event loop — set once during app startup
_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def register_run(run_id: str) -> asyncio.Queue:
    """Create a queue for run_id. Returns the queue."""
    q: asyncio.Queue = asyncio.Queue()
    _registry[run_id] = q
    return q


def get_queue(run_id: str) -> asyncio.Queue | None:
    return _registry.get(run_id)


def emit(run_id: str, step: str, message: str) -> None:
    """Thread-safe emit — safe to call from synchronous pipeline threads."""
    q = _registry.get(run_id)
    if q is None or _main_loop is None:
        return
    try:
        _main_loop.call_soon_threadsafe(q.put_nowait, {"step": step, "message": message})
    except Exception as exc:
        logger.debug("progress.emit error for %s: %s", run_id, exc)


def close_run(run_id: str) -> None:
    """Send done sentinel and remove queue from registry."""
    q = _registry.get(run_id)
    if q is not None and _main_loop is not None:
        try:
            _main_loop.call_soon_threadsafe(q.put_nowait, None)
        except Exception:
            pass
    _registry.pop(run_id, None)
