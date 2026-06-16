import pytest
from data_analysis_agent.config.settings import get_settings


def test_defaults(monkeypatch):
    monkeypatch.setenv("DATAANALYSIS_DATABASE_URL", "sqlite:///test.db")
    monkeypatch.delenv("DATAANALYSIS_OPENROUTER_API_KEY", raising=False)
    s = get_settings()
    assert s.database_url == "sqlite:///test.db"
    assert s.resolved_llm_provider == "stub"


def test_openrouter_provider_when_key_set(monkeypatch):
    monkeypatch.setenv("DATAANALYSIS_DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("DATAANALYSIS_OPENROUTER_API_KEY", "sk-or-fake-key-123")
    s = get_settings()
    assert s.resolved_llm_provider == "openrouter"


def test_inline_comment_stripped_from_key(monkeypatch):
    monkeypatch.setenv("DATAANALYSIS_DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("DATAANALYSIS_OPENROUTER_API_KEY", "  # empty comment  ")
    s = get_settings()
    assert s.resolved_llm_provider == "stub"
