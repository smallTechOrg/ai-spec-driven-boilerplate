import pytest

from agent.config import get_settings, validate_required_config


def test_env_comment_strip(monkeypatch):
    # Drive through ENV VARS (not init kwargs) — the APP_-prefix mapping only applies to env vars (C-ENV-STRIP).
    monkeypatch.setenv("APP_LLM_MODEL", "claude-haiku-4-5 # prod model")
    monkeypatch.setenv("APP_LLM_API_KEY", "sk-test-123 # prod key")
    get_settings.cache_clear()
    s = get_settings()
    assert s.llm_model == "claude-haiku-4-5"                      # inline comment + space stripped
    assert s.llm_api_key.get_secret_value() == "sk-test-123"     # SecretStr strip ran on the env value
    assert "sk-test-123" not in repr(s)                          # secret stays masked (C-SECRET-TYPE)
    get_settings.cache_clear()


def test_extra_env_key_ignored(monkeypatch):
    # An undeclared .env key (CI vars, TEST_DATABASE_URL) must NOT raise at startup (C-ENV-IGNORE).
    monkeypatch.setenv("APP_SOME_UNDECLARED_KEY", "whatever")
    monkeypatch.setenv("APP_LLM_API_KEY", "sk-test")
    get_settings.cache_clear()
    s = get_settings()                                            # must not raise
    assert s.llm_api_key.get_secret_value() == "sk-test"
    get_settings.cache_clear()


def test_validate_required_config_fails_loud(monkeypatch):
    monkeypatch.setenv("APP_LLM_API_KEY", "")                     # blank key
    get_settings.cache_clear()
    with pytest.raises(RuntimeError) as exc:
        validate_required_config()
    assert "APP_LLM_API_KEY" in str(exc.value)                   # the missing var is NAMED
    get_settings.cache_clear()
