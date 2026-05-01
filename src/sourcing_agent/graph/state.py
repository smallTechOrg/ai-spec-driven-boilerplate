from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    run_id: str
    request_id: str
    request: dict
    raw_results: list[dict]
    suppliers: list[dict]
    recommendations: list[dict]
    error: str | None
