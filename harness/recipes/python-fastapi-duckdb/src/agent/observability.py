"""Observability — one ``span()`` context manager for timing a unit of work.

Generic and storage-agnostic: enrich the yielded dict inside the block (args,
result preview, tokens) and the span is emitted as one structured log line on exit
(name, kind, duration_ms, attributes). Swap the log sink for OTel / a spans table
when you need durable traces.
"""

import time
from contextlib import asynccontextmanager

import structlog

log = structlog.get_logger()


@asynccontextmanager
async def span(name: str, kind: str = "INTERNAL", **attrs):
    start = time.time()
    try:
        yield attrs
    except Exception as exc:  # record then re-raise — never swallow
        attrs["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        duration_ms = int((time.time() - start) * 1000)
        log.info("span", name=name, kind=kind, duration_ms=duration_ms, **attrs)
