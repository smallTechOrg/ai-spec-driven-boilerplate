"""Offline LLM provider.

Branches on explicit node tags injected by each pipeline node — never on
prose keywords from the prompt body.
"""
from __future__ import annotations

import hashlib
import json
import re


class StubLLMProvider:
    name = "stub"

    def complete(self, prompt: str) -> str:
        if "<node:enrich>" in prompt:
            return _enrich_response(prompt)
        if "<node:score>" in prompt:
            return _score_response(prompt)
        return "[stub] no node tag found in prompt"


def _supplier_blocks(prompt: str) -> list[dict]:
    """Pull the JSON list of raw search results out of the prompt."""
    match = re.search(r"<results>(.*?)</results>", prompt, re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return []


def _enrich_response(prompt: str) -> str:
    raw = _supplier_blocks(prompt)
    enriched: list[dict] = []
    for r in raw:
        name = r.get("name", "Unknown Supplier")
        loc = r.get("location") or r.get("city") or "Unknown"
        url = r.get("url", "")
        h = hashlib.md5(name.encode()).hexdigest()
        price_tail = int(h[:2], 16) % 8 + 4  # ₹4–₹11 range
        lead_days = int(h[2:4], 16) % 10 + 3  # 3–12 days
        enriched.append(
            {
                "name": name,
                "location": loc,
                "price_indication": f"₹{price_tail}.50 / unit",
                "lead_time": f"{lead_days}–{lead_days + 2} days",
                "source_url": url,
                "notes": (
                    f"{name} operates out of {loc} and supplies the requested "
                    "category. Public listings indicate ISI-marked product "
                    "availability and willingness to negotiate MOQ. Logistics "
                    "are handled in-house with same-state delivery typical."
                ),
            }
        )
    return json.dumps(enriched)


def _score_response(prompt: str) -> str:
    suppliers = _supplier_blocks(prompt)
    out: list[dict] = []
    for i, s in enumerate(suppliers):
        h = hashlib.md5(s.get("name", str(i)).encode()).hexdigest()
        score = 70 + (int(h[:2], 16) % 25)  # 70..94
        rationale = (
            f"{s.get('name', 'Supplier')} scores {score} because it matches "
            f"on location ({s.get('location', 'n/a')}), offers a competitive "
            f"price ({s.get('price_indication', 'n/a')}) and an acceptable "
            f"lead time ({s.get('lead_time', 'n/a')}). Trade-offs: limited "
            "public reviews, MOQ to be confirmed, and price is indicative "
            "until a quote is requested."
        )
        out.append(
            {
                "supplier_name": s.get("name"),
                "score": score,
                "rationale": rationale,
            }
        )
    out.sort(key=lambda r: r["score"], reverse=True)
    return json.dumps(out)
