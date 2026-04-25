"""Unit tests for the LangGraph agent compilation."""

from sourcing_agent.graph.agent import build_graph
from sourcing_agent.graph.state import AgentState


def test_graph_compiles_without_env_vars():
    """Graph must compile with no environment variables set."""
    graph = build_graph()
    assert graph is not None


def test_agent_state_has_required_keys():
    state: AgentState = {
        "run_id": "test-id",
        "project_name": "Test",
        "materials": [],
        "supplier_candidates": {},
        "recommendations": {},
        "status": "pending",
        "error": None,
    }
    assert state["run_id"] == "test-id"
    assert state["status"] == "pending"
