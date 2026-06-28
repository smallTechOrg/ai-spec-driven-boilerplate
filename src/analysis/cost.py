"""Token → USD cost estimation for Gemini 2.5 Flash.

Pricing (per Google Gemini API list pricing for gemini-2.5-flash, paid tier):
  input  text:  $0.30 per 1M tokens
  output text:  $2.50 per 1M tokens
These are documented constants; if pricing changes, update here. They are an
estimate for per-question cost accounting, not a billing source of truth.
"""
from __future__ import annotations

# USD per single token.
PROMPT_USD_PER_TOKEN = 0.30 / 1_000_000
COMPLETION_USD_PER_TOKEN = 2.50 / 1_000_000


def estimate_cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost from prompt/completion token counts."""
    return (
        prompt_tokens * PROMPT_USD_PER_TOKEN
        + completion_tokens * COMPLETION_USD_PER_TOKEN
    )
