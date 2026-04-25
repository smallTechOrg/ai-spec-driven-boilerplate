from __future__ import annotations

import json

from sourcing_agent.llm.factory import create_llm_provider
from sourcing_agent.tools._prompts import load_prompt


def enrich_suppliers(
    raw_results: list[dict], material: str, location: str
) -> list[dict]:
    provider = create_llm_provider()
    prompt = load_prompt("enrich").format(
        material=material,
        location=location,
        results_json=json.dumps(raw_results),
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
