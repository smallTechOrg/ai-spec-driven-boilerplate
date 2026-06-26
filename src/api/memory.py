"""`/memory` routes (Phase 3) — the global persistent memory.

`spec/api.md`: read / replace the global persistent memory text. PATCH triggers
C31 compression (`compress_memory`). The memory is injected into every
`plan_action` prompt as authoritative. Always 200 on read; PATCH **400** when the
body is invalid (missing / non-string `global_memory`).

Reads/writes go through the helpers in `graph.memory` (the `settings` key/value
table). Compression runs synchronously on PATCH for deterministic behaviour in
the single-user app, but a compression failure NEVER 500s the request — the
helper returns [] on any failure and PATCH still returns 200.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, StrictStr, ValidationError

from api._common import ok, api_error
from graph.memory import (
    compress_memory,
    get_memory_facts,
    get_memory_text,
    set_memory_facts,
    set_memory_text,
)

router = APIRouter()


class MemoryPatch(BaseModel):
    """PATCH body. `global_memory` MUST be a string (empty string clears it).

    `StrictStr` rejects a number/bool/null coerced into a string, so
    `{"global_memory": 123}` or `null` is a 400 `invalid_body`.
    """

    global_memory: StrictStr


@router.get("/memory")
def get_memory() -> dict:
    """Read the global memory text + compressed facts. Always 200."""
    text = get_memory_text()
    facts = get_memory_facts()
    return ok(
        {
            "global_memory": text,
            "global_memory_facts": facts,
            "char_count": len(text),
            "fact_count": len(facts),
        }
    )


@router.patch("/memory")
async def patch_memory(request: Request) -> dict:
    """Replace the global memory text and re-run C31 compression.

    400 `invalid_body` when the body is not JSON or `global_memory` is missing /
    not a string. On a valid body: store the text, then synchronously compress to
    facts (failure -> [] facts, still 200). Always 200 on a valid body.
    """
    try:
        raw: Any = await request.json()
    except Exception:  # noqa: BLE001 — malformed / non-JSON body
        raise api_error("invalid_body", "Request body must be valid JSON.", 400)

    try:
        body = MemoryPatch.model_validate(raw)
    except ValidationError:
        raise api_error(
            "invalid_body",
            "`global_memory` is required and must be a string.",
            400,
        )

    text = body.global_memory
    set_memory_text(text)

    # C31 compression is synchronous here for determinism; a failure returns []
    # (never raises) so the PATCH always returns 200 on a valid body.
    facts = compress_memory(text)
    set_memory_facts(facts)

    return ok({"global_memory": text, "global_memory_facts": facts})
