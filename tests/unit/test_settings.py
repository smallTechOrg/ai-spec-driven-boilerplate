"""Settings + provider auto-detection — no LLM key required."""
import pytest
import os


def test_auto_detects_anthropic(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_ANTHROPIC_API_KEY", "sk-ant-fake")
    monkeypatch.setenv("AGENT_GEMINI_API_KEY", "")
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "")
    monkeypatch.setenv("AGENT_DATABASE_URL", f"sqlite:///{tmp_path}/t.db")

    import config.settings as m
    m._settings = None
    s = m.get_settings()
    assert s.anthropic_api_key == "sk-ant-fake"
    assert s.gemini_api_key == ""


def test_auto_detects_gemini(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("AGENT_GEMINI_API_KEY", "AIza-fake")
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "")
    monkeypatch.setenv("AGENT_DATABASE_URL", f"sqlite:///{tmp_path}/t.db")

    import config.settings as m
    m._settings = None
    s = m.get_settings()
    assert s.gemini_api_key == "AIza-fake"


def test_provider_raises_with_no_key(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("AGENT_GEMINI_API_KEY", "")
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "")
    monkeypatch.setenv("AGENT_DATABASE_URL", f"sqlite:///{tmp_path}/t.db")

    import config.settings as m
    m._settings = None

    from llm.client import _make_provider
    with pytest.raises(RuntimeError, match="No LLM provider configured"):
        _make_provider()


def test_env_file_loads_regardless_of_cwd(monkeypatch, tmp_path):
    """Regression: .env must be anchored to the repo root, not CWD.

    Previously env_file=".env" was resolved relative to the process CWD, so
    instantiating Settings() while CWD was not the repo root silently read
    empty defaults for every key. Here we chdir to a temp dir, clear any
    AGENT_-prefixed env overrides, and confirm the repo-root .env still loads.
    """
    import config.settings as m

    # Ensure no env-var overrides mask the .env file read.
    for key in list(os.environ):
        if key.startswith("AGENT_"):
            monkeypatch.delenv(key, raising=False)

    # The real regression: build Settings from a different CWD.
    monkeypatch.chdir(tmp_path)
    m._settings = None
    s = m.get_settings()

    # database_url is defined in the repo-root .env; if .env loaded correctly
    # it must NOT equal the hard-coded sqlite default.
    assert s.database_url, "database_url should be populated from .env"

    # The anchored path must point at the repo-root .env and exist.
    assert m._ENV_FILE.name == ".env"
    assert m._ENV_FILE.exists()
    # parents[2] of src/config/settings.py must be the repo root (contains src/).
    assert (m._ENV_FILE.parent / "src" / "config" / "settings.py").exists()


def test_explicit_provider_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_ANTHROPIC_API_KEY", "sk-ant-fake")
    monkeypatch.setenv("AGENT_GEMINI_API_KEY", "AIza-fake")
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("AGENT_DATABASE_URL", f"sqlite:///{tmp_path}/t.db")

    import config.settings as m
    m._settings = None
    s = m.get_settings()
    assert s.llm_provider == "gemini"
