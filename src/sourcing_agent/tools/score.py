from __future__ import annotations

import json

from sourcing_agent.llm.factory import create_llm_provider
from sourcing_agent.tools._prompts import load_prompt


def score_suppliers(
    suppliers: list[dict],
    material: str,
    location: str,
    quantity: str,
    budget: str | None,
    timeline: str | None,
    criteria: str | None,
) -> list[dict]:
    provider = create_llm_provider()
    prompt = load_prompt("score").format(
        material=material,
        location=location,
        quantity=quantity,
        budget=budget or "(unspecified)",
        timeline=timeline or "(unspecified)",
        criteria=criteria or "(unspecified)",
        suppliers_json=json.dumps(suppliers),
    )
    response = provider.complete(prompt)
    return _parse_json_list(response)


def _parse_json_list(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []
