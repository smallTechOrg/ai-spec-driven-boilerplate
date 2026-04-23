from blogforge.graph.agent import build_graph


def test_graph_compiles():
    g = build_graph()
    assert g is not None
