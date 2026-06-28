"""Routing logic for the agentic loop — no LLM key required."""
from graph.edges import route_after_verify


def test_valid_result_routes_to_finalize():
    state = {"exec_result": {"a": 1}, "last_error": None, "step": 0, "max_steps": 4}
    assert route_after_verify(state) == "finalize"


def test_recoverable_error_under_cap_retries():
    state = {"exec_result": None, "last_error": "boom", "step": 0, "max_steps": 4}
    assert route_after_verify(state) == "plan"


def test_recoverable_error_at_cap_goes_to_handle_error():
    state = {"exec_result": None, "last_error": "boom", "step": 3, "max_steps": 4}
    assert route_after_verify(state) == "handle_error"


def test_fatal_error_goes_to_handle_error():
    state = {"error": "missing key", "step": 0, "max_steps": 4}
    assert route_after_verify(state) == "handle_error"
