from __future__ import annotations

from typing import TypedDict, Any

from lead_gen_agent.domain.models import Candidate, Lead


class AgentState(TypedDict, total=False):
    run_id: str
    country: str
    industry: str
    size_band: str

    search_results: list[dict]
    candidates: list[Candidate]
    leads: list[Lead]

    status: str
    error: str | None
