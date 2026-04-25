"""Stub LLM provider — returns hardcoded responses for offline testing.

Node tags injected by graph nodes determine which stub branch fires.
Tags are NEVER matched on prose keywords from the prompt body.
"""

import json

from sourcing_agent.llm.providers.base import LLMProvider

_STUB_RESEARCH_RESPONSE = json.dumps([
    {
        "supplier_name": "BuildMart Supplies Co.",
        "supplier_location": "Chicago, IL",
        "price_per_unit": 12.50,
        "currency": "USD",
        "lead_time_days": 7,
        "certifications": ["ISO 9001", "ISO 14001"],
        "notes": "<node:research> Stub: reliable mid-tier supplier with broad product range.",
    },
    {
        "supplier_name": "PrimeMaterials Ltd.",
        "supplier_location": "Detroit, MI",
        "price_per_unit": 10.80,
        "currency": "USD",
        "lead_time_days": 14,
        "certifications": ["ISO 9001"],
        "notes": "<node:research> Stub: budget-friendly, longer lead time.",
    },
    {
        "supplier_name": "EliteConstruct Distributors",
        "supplier_location": "Cincinnati, OH",
        "price_per_unit": 15.20,
        "currency": "USD",
        "lead_time_days": 3,
        "certifications": ["ISO 9001", "ISO 14001", "CE Mark"],
        "notes": "<node:research> Stub: premium quality, fast delivery, certified.",
    },
])


class StubLLMProvider(LLMProvider):
    """Returns canned responses keyed on node tags in the prompt."""

    def generate(self, prompt: str) -> str:
        if "<node:research>" in prompt:
            return _STUB_RESEARCH_RESPONSE
        # Fallback for any unrecognised node
        return json.dumps([])
