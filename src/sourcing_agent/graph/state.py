"""LangGraph agent state definition."""

from typing import TypedDict


class AgentState(TypedDict):
    # Identity
    run_id: str
    project_name: str

    # Pipeline input (set by intake_node from DB)
    materials: list[dict]  # [{name, quantity, unit}, ...]

    # Pipeline data (populated progressively)
    supplier_candidates: dict[str, list[dict]]  # material_name → list of candidate dicts
    recommendations: dict[str, list[dict]]       # material_name → ranked list of candidate dicts

    # Control
    status: str
    error: str | None
