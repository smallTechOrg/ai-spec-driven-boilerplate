def test_graph_compiles():
    from graph.agent import profile_graph, qa_graph
    assert profile_graph is not None
    assert qa_graph is not None


def test_settings_loads():
    from config.settings import get_settings
    s = get_settings()
    assert s.database_url


def test_api_creates():
    from api import app
    assert app is not None
