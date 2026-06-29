def test_graph_compiles():
    """Both graphs compile without requiring any env vars."""
    from graph.agent import profile_graph, qa_graph
    assert profile_graph is not None
    assert qa_graph is not None
