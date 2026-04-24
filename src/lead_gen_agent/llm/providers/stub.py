"""Stub LLM provider.

Branches purely on explicit `<node:*>` tags in the prompt, never on prose keywords
(repo rule 8). Draft/extract output is article-shaped, not bare bullets.
"""
from __future__ import annotations

import hashlib
import json


def _hash_score(text: str) -> int:
    h = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
    return 40 + (h % 55)  # 40..94 so every stub lead is a plausibly interesting prospect


class StubProvider:
    def complete(self, prompt: str) -> str:
        if "<node:extract>" in prompt:
            return self._extract()
        if "<node:score>" in prompt:
            return self._score(prompt)
        if "<node:search>" in prompt:
            return "stub-search"
        return "stub-unknown-node"

    def _extract(self) -> str:
        records = [
            {
                "name": "Müller Präzisionstechnik GmbH",
                "website": "https://mueller-praezision.example.de",
                "hq_city": "Stuttgart",
                "description": (
                    "Family-owned precision-engineering manufacturer serving Tier-2 automotive suppliers since 1978.\n\n"
                    "Around 80 staff across a single facility in Stuttgart. Website mentions CNC milling and ISO-9001 certification; "
                    "no careers page, no named CTO, no reference to data, analytics, or BI."
                ),
            },
            {
                "name": "Nordlicht Logistik AG",
                "website": "https://nordlicht-logistik.example.de",
                "hq_city": "Hamburg",
                "description": (
                    "Regional freight & warehousing SMB operating a fleet of ~30 trucks across northern Germany.\n\n"
                    "Family-run for two generations. Fleet tracked via a third-party telematics vendor; internal tooling is "
                    "Excel + QuickBooks per the public job ad for an office administrator."
                ),
            },
            {
                "name": "Rheinblick Weinhandel",
                "website": "https://rheinblick.example.de",
                "hq_city": "Koblenz",
                "description": (
                    "Wholesale wine trader with 25 staff, sourcing from Rhine vintners and supplying restaurants across "
                    "Rhineland-Palatinate.\n\n"
                    "Traditional retail + HORECA supply. No mention of any data, analytics, or tech role on their site; "
                    "the only IT-adjacent hire advertised in the past year was 'office IT support'."
                ),
            },
        ]
        return json.dumps(records)

    def _score(self, prompt: str) -> str:
        score = _hash_score(prompt)
        rationale = (
            "Small size band, traditional industry, no evidence of data roles or analytics tooling on their site "
            "— strong candidate for outside data support."
        )
        return json.dumps({"score": score, "rationale": rationale})
