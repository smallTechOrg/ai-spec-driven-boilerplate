"""Cost estimation — no LLM key required."""
from data.cost import (
    FLASH_COMPLETION_USD_PER_1K,
    FLASH_PROMPT_USD_PER_1K,
    estimate_cost,
)


def test_estimate_cost_is_positive_for_real_token_counts():
    cost = estimate_cost(812, 240)
    expected = (
        812 / 1000 * FLASH_PROMPT_USD_PER_1K
        + 240 / 1000 * FLASH_COMPLETION_USD_PER_1K
    )
    assert cost > 0
    assert abs(cost - round(expected, 8)) < 1e-9


def test_estimate_cost_zero_tokens_is_zero():
    assert estimate_cost(0, 0) == 0.0


def test_estimate_cost_treats_negative_tokens_as_zero():
    assert estimate_cost(-5, -5) == 0.0


def test_completion_tokens_cost_more_than_prompt_tokens():
    # Output is priced higher than input on the flash tier.
    assert estimate_cost(0, 1000) > estimate_cost(1000, 0)
