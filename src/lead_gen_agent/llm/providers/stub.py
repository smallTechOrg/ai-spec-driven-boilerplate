"""Stub LLM provider — returns deterministic offline responses.

Each pipeline node injects a unique tag (<node:search>, <node:enrich>,
<node:contact>) into its prompt. The stub branches on those tags — never
on prose keywords.
"""
from __future__ import annotations

import json

from lead_gen_agent.llm.providers.base import LLMProvider


_STUB_SEARCH_RESPONSE = json.dumps([
    {"name": "Müller Logistik GmbH", "domain": "mueller-logistik.de", "website": "https://mueller-logistik.de"},
    {"name": "Nordic Retail AB", "domain": "nordicretail.se", "website": "https://nordicretail.se"},
    {"name": "Benelux Foods NV", "domain": "beneluxfoods.be", "website": "https://beneluxfoods.be"},
    {"name": "Adriatic Marine d.o.o.", "domain": "adriaticmarine.hr", "website": "https://adriaticmarine.hr"},
    {"name": "Iberian Components SL", "domain": "iberiancomponents.es", "website": "https://iberiancomponents.es"},
])

_STUB_ENRICH_RESPONSE = json.dumps({
    "industry": "Manufacturing",
    "headcount_estimate": "20-100",
    "why_fit": (
        "This company operates in a data-intensive sector but shows no signs of an "
        "in-house analytics team based on their public job listings and LinkedIn presence. "
        "A data consultant could unlock significant operational efficiency gains."
    ),
})

_STUB_CONTACT_RESPONSE = json.dumps([
    {
        "name": "Anna Müller",
        "title": "CEO",
        "email": "a.mueller@example.com",
        "phone": None,
        "linkedin_url": "https://linkedin.com/in/stub-profile",
    },
    {
        "name": "Thomas Bauer",
        "title": "Head of Operations",
        "email": None,
        "phone": "+49 30 12345678",
        "linkedin_url": None,
    },
])


class StubLLMProvider(LLMProvider):
    def generate(self, prompt: str) -> str:
        if "<node:search>" in prompt:
            return _STUB_SEARCH_RESPONSE
        if "<node:enrich>" in prompt:
            return _STUB_ENRICH_RESPONSE
        if "<node:contact>" in prompt:
            return _STUB_CONTACT_RESPONSE
        return '{"result": "stub response"}'
