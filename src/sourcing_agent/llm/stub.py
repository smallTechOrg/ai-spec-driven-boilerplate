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
    match = re.search(r"<results>(.*?)</results>", prompt, re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return []


_RELIABILITY = ["high", "mixed", "high", "mixed", "low"]
_SOLVENCY = ["stable", "stable", "unclear", "stable", "weak"]


def _enrich_response(prompt: str) -> str:
    raw = _supplier_blocks(prompt)
    enriched: list[dict] = []
    for i, r in enumerate(raw):
        name = r.get("name", "Unknown Supplier")
        loc = r.get("location") or r.get("city") or "Unknown"
        url = r.get("url", "")
        h = hashlib.md5(name.encode()).hexdigest()
        price_tail = int(h[:2], 16) % 8 + 4
        lead_days = int(h[2:4], 16) % 10 + 3
        rating = round(3.6 + (int(h[4:6], 16) % 14) / 10, 1)  # 3.6–4.9
        reviews = 25 + int(h[6:9], 16) % 600
        years = 4 + int(h[9:11], 16) % 22
        gst = (int(h[11], 16) % 4) != 0  # most have GST
        rel = _RELIABILITY[i % len(_RELIABILITY)]
        sol = _SOLVENCY[i % len(_SOLVENCY)]

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
                    "availability and willingness to negotiate MOQ."
                ),
                "google_rating": rating,
                "google_review_count": reviews,
                "feedback_summary": (
                    f"Reviewers consistently mention {name}'s product quality "
                    f"and responsiveness on quotes. Common praise: pricing is "
                    "competitive and ISI grading matches the listing. Common "
                    "concerns: occasional packaging damage in transit and "
                    "follow-up after delivery."
                ),
                "delivery_reliability": (
                    f"{rel} (based on {reviews} reviews mentioning on-time "
                    "delivery within the quoted window)"
                ),
                "years_in_business": years,
                "solvency_signal": (
                    f"{sol} (registered ~{years} years; "
                    f"{'GSTIN visible on listings' if gst else 'no public GSTIN found'})"
                ),
                "gst_registered": gst,
            }
        )
    return json.dumps(enriched)


def _score_response(prompt: str) -> str:
    suppliers = _supplier_blocks(prompt)
    out: list[dict] = []
    for i, s in enumerate(suppliers):
        h = hashlib.md5(s.get("name", str(i)).encode()).hexdigest()
        score = 70 + (int(h[:2], 16) % 25)
        rationale = (
            f"{s.get('name', 'Supplier')} scores {score} because it matches "
            f"on location ({s.get('location', 'n/a')}), offers a competitive "
            f"price ({s.get('price_indication', 'n/a')}), and an acceptable "
            f"lead time ({s.get('lead_time', 'n/a')}). Reviews "
            f"({s.get('google_rating', 'n/a')}★ across "
            f"{s.get('google_review_count', 'n/a')} ratings) and a "
            f"{s.get('solvency_signal', 'n/a').split(' (', 1)[0]} solvency "
            "signal support the ranking. Trade-offs: quote needed to confirm "
            "MOQ and final delivery window."
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
