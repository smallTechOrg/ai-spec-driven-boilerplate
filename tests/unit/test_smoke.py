def test_package_imports():
    import sourcing_agent

    assert sourcing_agent.__version__ == "0.1.0"


def test_settings_resolve_to_stub_without_keys():
    from sourcing_agent.config.settings import get_settings

    s = get_settings()
    assert s.resolved_llm_provider == "stub"
    assert s.resolved_search_provider == "stub"


def test_settings_strip_inline_comment(monkeypatch):
    monkeypatch.setenv("SOURCING_LLM_PROVIDER", "stub   # auto | gemini | stub")
    import sourcing_agent.config.settings as m

    m._settings = None
    s = m.get_settings()
    assert s.resolved_llm_provider == "stub"
