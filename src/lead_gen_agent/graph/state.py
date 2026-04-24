"""AgentState — the single mutable object passed between graph nodes."""
from __future__ import annotations

from typing import TypedDict

from lead_gen_agent.domain import LeadCreate, SearchCriteria


class AgentState(TypedDict):
    # Identity
    run_id: str
    criteria: SearchCriteria

    # Pipeline data (populated progressively by nodes)
    raw_companies: list[dict]       # [{name, domain, website}, ...]
    leads: list[LeadCreate]         # enriched lead objects ready to save

    # Control
    error: str | None               # set by any node on fatal failure
