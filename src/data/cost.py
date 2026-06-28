"""Token-to-USD cost estimation for the Gemini flash tier.

Prices are USD per 1,000 tokens. The constants are intentionally explicit and
configurable so the audit cost stays accurate if pricing changes. They reflect
the published `gemini-2.5-flash` rates (input/output) as of mid-2026.
"""

# USD per 1,000 tokens for gemini-2.5-flash.
FLASH_PROMPT_USD_PER_1K = 0.0003
FLASH_COMPLETION_USD_PER_1K = 0.0025


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    *,
    prompt_usd_per_1k: float = FLASH_PROMPT_USD_PER_1K,
    completion_usd_per_1k: float = FLASH_COMPLETION_USD_PER_1K,
) -> float:
    """Return the estimated USD cost for a run given real token counts.

    Cost = prompt_tokens/1000 * prompt_price + completion_tokens/1000 * completion_price.
    """
    prompt_tokens = max(0, int(prompt_tokens or 0))
    completion_tokens = max(0, int(completion_tokens or 0))
    cost = (
        prompt_tokens / 1000.0 * prompt_usd_per_1k
        + completion_tokens / 1000.0 * completion_usd_per_1k
    )
    return round(cost, 8)
