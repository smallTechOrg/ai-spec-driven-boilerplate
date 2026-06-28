"""The single privacy chokepoint between the agent and the LLM.

EVERY LLM payload on the analysis path is built here. The payload may contain
ONLY: the dataset profile (column schema/stats), a TINY capped sample (<=N rows),
the question, and prior conversation turns. It must NEVER contain the full row
set. ``build_llm_context`` returns the exact serialised string sent to Gemini so
tests can assert the boundary holds.

It also exposes ``call_llm`` — the usage-aware wrapper the nodes call. It uses
the existing provider abstraction (``LLMClient``) for the model default/auth and
captures real token usage from Gemini's ``usage_metadata`` so cost can be
accounted. (The skeleton ``LLMClient.call_model`` returns text only and does not
surface usage; rather than edit the provider — owned by another surface — this
chokepoint reads usage directly from the Gemini response and falls back to a
character-based estimate if usage is unavailable. This is the documented usage
gap.)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from config.settings import get_settings

MAX_SAMPLE_ROWS = 5
MAX_HISTORY_TURNS = 6
DEFAULT_MODEL = "gemini-2.5-flash"

# Gemini 2.5 Flash approximate pricing (USD per 1M tokens). Used only for the
# estimated_cost_usd accounting field.
_COST_PER_M_INPUT = 0.30
_COST_PER_M_OUTPUT = 2.50


def build_llm_context(
    *,
    question: str,
    profile: list[dict] | None,
    sample_rows: list[dict] | None,
    history: list[dict] | None = None,
    row_count: int | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """Build the EXACT serialised LLM payload — the privacy boundary.

    Only profile + capped sample + question + capped history (+ optional small
    ``extra`` such as a plan or a traceback) ever appear. The full row set is
    never included. Returns a JSON string.
    """
    capped_sample = (sample_rows or [])[:MAX_SAMPLE_ROWS]
    capped_history = (history or [])[-MAX_HISTORY_TURNS:]

    payload: dict[str, Any] = {
        "question": question,
        "dataset": {
            "row_count": row_count,
            "profile": profile or [],
            "sample_rows": capped_sample,
            "sample_note": (
                f"This is a {len(capped_sample)}-row sample of a "
                f"{row_count if row_count is not None else 'larger'}-row dataset. "
                "You never see the full data; generate code that runs locally "
                "over ALL rows."
            ),
        },
        "history": [
            {"question": h.get("question"), "answer": h.get("answer")}
            for h in capped_history
        ],
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload, ensure_ascii=False, default=str)


@dataclass
class LLMResult:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0


def _estimate_tokens(text: str) -> int:
    # ~4 chars/token rough fallback when usage metadata is unavailable.
    return max(1, len(text) // 4)


def _model_name() -> str:
    s = get_settings()
    return s.llm_model or DEFAULT_MODEL


def call_llm(user_payload: str, *, system: str) -> LLMResult:
    """Call Gemini with a system prompt + the privacy-safe user payload.

    Captures real prompt/completion token usage from the Gemini response when
    available; otherwise falls back to a char-based estimate. Returns an
    ``LLMResult`` with text + usage + estimated cost.
    """
    s = get_settings()
    model = _model_name()
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=s.gemini_api_key)
        config = types.GenerateContentConfig(system_instruction=system)
        response = client.models.generate_content(
            model=model, contents=user_payload, config=config
        )
        text = response.text or ""
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
        completion_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
    except Exception:
        # No fabricated success — re-raise so the node routes to handle_error.
        raise

    if prompt_tokens == 0:
        prompt_tokens = _estimate_tokens(system + user_payload)
    if completion_tokens == 0:
        completion_tokens = _estimate_tokens(text)

    cost = (
        prompt_tokens / 1_000_000 * _COST_PER_M_INPUT
        + completion_tokens / 1_000_000 * _COST_PER_M_OUTPUT
    )
    return LLMResult(
        text=text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost,
    )
