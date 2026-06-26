"""C31 dataset context compression (`extract_facts`).

`spec/agent.md` -> "## Graph-adjacent single LLM calls": after C30 generates a
dataset's notes (`datasets.context`), this module distils those notes into a short
list of structured facts (`datasets.context_facts`, <= 20) with ONE `LLMClient`
call. Keeping the prompt small is the whole point — the facts are injected into the
`plan_action` prompt instead of the full notes.

This is the DATASET-scoped sibling of `graph.memory.compress_memory` (which
compresses the GLOBAL `settings.global_memory`). Both reuse `compress.md`. The
parse helper here is a small local copy of memory's `_parse_facts` so this file
owns its own behaviour without editing `memory.py`.

Per the spec's "async fire-and-forget self-heal variants guarded by an in-flight
lock": concurrent triggers for the SAME dataset must not double-run, so
`extract_facts(dataset_id)` takes a per-dataset lock and no-ops a second concurrent
call. Failures return `[]` (or leave `[]` on the row) and NEVER raise.

All LLM calls go through `LLMClient` (never a provider SDK directly).
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from db.models import DatasetRow
from db.session import create_db_session
from llm.client import LLMClient
from observability.events import get_logger

logger = get_logger("graph.compress")

# At most this many compressed facts per scope (spec: "compressed facts <= 20").
_MAX_FACTS = 20

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_COMPRESS_PROMPT_PATH = _PROMPTS_DIR / "compress.md"

# Node tag so the stub provider can branch deterministically. The stub has no
# `<node:compress>` branch, so OFFLINE the reply is non-JSON and the parse below
# yields [] by design (graceful). The authoritative gate is real Gemini.
_COMPRESS_TAG = "<node:compress>"

# Per-dataset in-flight locks so concurrent triggers don't double-run (spec's
# "in-flight lock" note). Guarded by `_locks_guard`.
_locks_guard = threading.Lock()
_inflight: dict[str, threading.Lock] = {}


def _dataset_lock(dataset_id: str) -> threading.Lock:
    with _locks_guard:
        lock = _inflight.get(dataset_id)
        if lock is None:
            lock = threading.Lock()
            _inflight[dataset_id] = lock
        return lock


def _parse_facts(reply: str) -> list[str]:
    """Parse a JSON array of strings from the model reply; [] on any failure.

    Tolerates a bare array or one wrapped in a fence / surrounding prose by
    extracting the first `[...]` span before parsing. Caps at `_MAX_FACTS`.
    """
    if not reply:
        return []
    raw = reply.strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        parsed = json.loads(raw[start : end + 1])
    except Exception:  # noqa: BLE001 — non-JSON reply (e.g. stub fallback)
        return []
    if not isinstance(parsed, list):
        return []
    facts = [str(f).strip() for f in parsed if str(f).strip()]
    return facts[:_MAX_FACTS]


def extract_facts_from_text(text: str) -> list[str]:
    """Distil arbitrary notes text into <= 20 atomic facts via ONE LLM call.

    Returns [] on ANY failure (empty input, LLM error, parse error) — never
    raises. Offline (stub) the reply is non-JSON, so this returns [] by design.
    """
    if not (text or "").strip():
        return []
    try:
        system = _COMPRESS_PROMPT_PATH.read_text(encoding="utf-8").strip()
        prompt = (
            f"{_COMPRESS_TAG}\n\n"
            "## Notes text\n"
            f"{text.strip()}\n\n"
            "Output a JSON array of at most 20 concise factual statements distilled "
            "from the notes above. Output ONLY the JSON array."
        )
        reply = LLMClient().call_model(prompt, system=system)
    except Exception as exc:  # noqa: BLE001 — compression failure is non-fatal
        logger.warning("extract_facts_failed", error=str(exc))
        return []
    return _parse_facts(reply)


def extract_facts(dataset_id: str) -> list[str]:
    """C31 for a dataset: compress its `context` notes into `context_facts`.

    Reads the dataset's `context`, runs ONE LLM compression call, and writes the
    resulting <= 20 facts to `datasets.context_facts`. Guarded by a per-dataset
    in-flight lock so concurrent triggers for the SAME dataset do not double-run
    (a second concurrent call no-ops and returns the existing facts). Returns the
    facts written ([] on any failure) and NEVER raises.
    """
    lock = _dataset_lock(dataset_id)
    if not lock.acquire(blocking=False):
        # Another extraction for this dataset is already running — don't double-run.
        logger.info("extract_facts_inflight_skip", dataset_id=dataset_id)
        try:
            with create_db_session() as session:
                row = session.get(DatasetRow, dataset_id)
                return list(row.context_facts or []) if row is not None else []
        except Exception:  # noqa: BLE001 — best-effort read
            return []
    try:
        try:
            with create_db_session() as session:
                row = session.get(DatasetRow, dataset_id)
                context = (row.context or "") if row is not None else ""
            if row is None:
                return []
        except Exception as exc:  # noqa: BLE001 — read failure is non-fatal
            logger.warning("extract_facts_read_failed", dataset_id=dataset_id, error=str(exc))
            return []

        facts = extract_facts_from_text(context)

        try:
            with create_db_session() as session:
                row = session.get(DatasetRow, dataset_id)
                if row is not None:
                    row.context_facts = facts
        except Exception as exc:  # noqa: BLE001 — write failure is non-fatal
            logger.warning("extract_facts_write_failed", dataset_id=dataset_id, error=str(exc))
            return []

        logger.info("extract_facts_ok", dataset_id=dataset_id, fact_count=len(facts))
        return facts
    finally:
        lock.release()
