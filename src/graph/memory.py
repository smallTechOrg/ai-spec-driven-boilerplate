"""Global persistent memory (the `settings` table) + C31 compression.

`spec/agent.md` -> "## Memory & Context": across runs, the SQLite `settings`
table stores the user-authoritative `global_memory` text plus its compressed
`global_memory_facts`, both injected into every `plan_action` prompt as ground
truth. This module owns the read/write helpers and the C31 `extract_facts`
(`compress_memory`) single LLM call.

The injection helper `get_memory_block()` is imported by `graph.nodes.plan_action`
(slice-3b owns the import line) and is called on EVERY iteration of EVERY run, so
it (and the reads it depends on) must NEVER raise — they return "" / [] on any
error instead.

All LLM calls go through `LLMClient` (never a provider SDK directly).
"""
from __future__ import annotations

import json
from pathlib import Path

from db.models import SettingRow
from db.session import create_db_session
from llm.client import LLMClient
from observability.events import get_logger

logger = get_logger("graph.memory")

# Well-known DB keys in the key/value `settings` table.
MEMORY_TEXT_KEY = "global_memory"
MEMORY_FACTS_KEY = "global_memory_facts"

# At most this many compressed facts per scope (spec: "compressed facts <= 20").
_MAX_FACTS = 20

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_COMPRESS_PROMPT_PATH = _PROMPTS_DIR / "compress.md"

# Node tag so the stub provider can branch deterministically. The stub has no
# `<node:compress>` branch (owned by slice-2a) — it falls through to its plan
# fallback, producing a non-JSON reply, so `compress_memory` returns [] offline
# by design (the parse-fail path below handles it gracefully).
_COMPRESS_TAG = "<node:compress>"


# --------------------------------------------------------------------------- #
# Raw read / write helpers (settings key/value table)
# --------------------------------------------------------------------------- #


def get_memory_text() -> str:
    """The authoritative global memory text ("" when unset). Never raises."""
    try:
        with create_db_session() as session:
            row = session.get(SettingRow, MEMORY_TEXT_KEY)
            if row is None or row.value is None:
                return ""
            return row.value
    except Exception as exc:  # noqa: BLE001 — read must never break a run
        logger.warning("get_memory_text_failed", error=str(exc))
        return ""


def get_memory_facts() -> list[str]:
    """The compressed global facts ([] when unset/unparseable). Never raises."""
    try:
        with create_db_session() as session:
            row = session.get(SettingRow, MEMORY_FACTS_KEY)
            if row is None or not row.value:
                return []
            parsed = json.loads(row.value)
        if not isinstance(parsed, list):
            return []
        return [str(f) for f in parsed if str(f).strip()]
    except Exception as exc:  # noqa: BLE001 — read must never break a run
        logger.warning("get_memory_facts_failed", error=str(exc))
        return []


def _upsert(session, key: str, value: str | None) -> None:
    row = session.get(SettingRow, key)
    if row is None:
        session.add(SettingRow(key=key, value=value))
    else:
        row.value = value


def set_memory_text(text: str) -> None:
    """Upsert the `global_memory` row (insert or update value + updated_at)."""
    with create_db_session() as session:
        _upsert(session, MEMORY_TEXT_KEY, text)


def set_memory_facts(facts: list[str]) -> None:
    """Upsert `global_memory_facts` as a JSON-encoded list of strings."""
    capped = [str(f) for f in (facts or [])][:_MAX_FACTS]
    with create_db_session() as session:
        _upsert(session, MEMORY_FACTS_KEY, json.dumps(capped))


# --------------------------------------------------------------------------- #
# Injection block (imported by slice-3b's plan_action — must NEVER raise)
# --------------------------------------------------------------------------- #


def get_memory_block() -> str:
    """The persistent-memory block injected into every `plan_action` prompt.

    Combines the authoritative memory text and the compressed facts into one
    block. Returns "" (empty) when there is no memory and no facts, so the
    injection adds nothing. NEVER raises — returns "" on any error.
    """
    try:
        text = get_memory_text().strip()
        facts = get_memory_facts()
        if not text and not facts:
            return ""

        parts: list[str] = [
            "The user has provided this authoritative context — treat it as ground truth:"
        ]
        if text:
            parts.append(text)
        if facts:
            parts.append("Key facts:")
            parts.extend(f"- {fact}" for fact in facts)
        return "\n".join(parts)
    except Exception as exc:  # noqa: BLE001 — injection must never break a run
        logger.warning("get_memory_block_failed", error=str(exc))
        return ""


# --------------------------------------------------------------------------- #
# C31 compression (`extract_facts`) — triggered by PATCH /memory
# --------------------------------------------------------------------------- #


def _parse_facts(reply: str) -> list[str]:
    """Parse a JSON array of strings from the model reply; [] on any failure.

    Tolerates a bare array or one wrapped in a markdown fence / surrounding prose
    by extracting the first `[...]` span before parsing. Caps at 20.
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


def compress_memory(text: str) -> list[str]:
    """C31 `extract_facts`: distil memory text into <=20 atomic facts.

    ONE `LLMClient.call_model` call with `compress.md` as system and a
    `<node:compress>`-tagged user prompt. Returns [] on ANY failure (LLM error,
    parse error) — never raises. Offline (stub) the reply is non-JSON, so this
    returns [] by design.
    """
    if not (text or "").strip():
        return []
    try:
        system = _COMPRESS_PROMPT_PATH.read_text(encoding="utf-8").strip()
        prompt = (
            f"{_COMPRESS_TAG}\n\n"
            "## Memory text\n"
            f"{text.strip()}\n\n"
            "Output a JSON array of at most 20 concise factual statements distilled "
            "from the memory text above. Output ONLY the JSON array."
        )
        reply = LLMClient().call_model(prompt, system=system)
    except Exception as exc:  # noqa: BLE001 — compression failure is non-fatal
        logger.warning("compress_memory_failed", error=str(exc))
        return []
    return _parse_facts(reply)
