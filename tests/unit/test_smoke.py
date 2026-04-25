"""Smoke test — package imports and version are correct."""

import sourcing_agent


def test_version():
    assert sourcing_agent.__version__ == "0.1.0"


def test_graph_compiles():
    """Graph must compile without any env vars set."""
    from sourcing_agent.graph.agent import build_graph

    graph = build_graph()
    assert graph is not None
