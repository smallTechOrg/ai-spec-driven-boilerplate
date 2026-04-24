"""Unit test — the graph compiles without any env vars."""
from lead_gen_agent.graph.agent import build_graph


def test_graph_compiles():
    g = build_graph()
    compiled = g.compile()
    assert compiled is not None
