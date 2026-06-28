"""Ask a question against a dataset; run the agent (Phase 1)."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from api._common import api_error, ok
from domain.run import AskRequest
from graph.runner import DatasetNotFound, run_agent

router = APIRouter()

# Substrings that indicate the LLM provider itself was unreachable (502 vs 500).
_LLM_UNAVAILABLE_HINTS = (
    "deadline",
    "unavailable",
    "connection",
    "timed out",
    "timeout",
    "rate limit",
    "resource_exhausted",
    "503",
    "502",
    "500 internal",
    "api key",
    "permission",
)


def _looks_like_llm_outage(message: str | None) -> bool:
    if not message:
        return False
    low = message.lower()
    return any(h in low for h in _LLM_UNAVAILABLE_HINTS)


@router.post("/ask")
async def ask(req: AskRequest) -> dict:
    question = (req.question or "").strip()
    if not question:
        raise api_error("BAD_REQUEST", "Question must not be empty", 400)

    try:
        payload = await run_in_threadpool(
            run_agent, req.dataset_id, question, req.conversation_id
        )
    except DatasetNotFound:
        raise api_error("NOT_FOUND", f"Dataset {req.dataset_id} not found", 404)
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if _looks_like_llm_outage(msg):
            raise api_error("LLM_UNAVAILABLE", f"LLM unavailable: {msg}", 502)
        raise api_error("RUN_FAILED", f"Agent run failed: {msg}", 500)

    if payload.get("status") == "failed":
        err = payload.get("error_message") or "Agent run failed"
        if _looks_like_llm_outage(err):
            raise api_error("LLM_UNAVAILABLE", f"LLM unavailable: {err}", 502)
        raise api_error("RUN_FAILED", err, 500)

    return ok(payload)
