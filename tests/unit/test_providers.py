"""Offline provider tests — zero env, no network, no API key.

Covers the `_make_provider()` factory auto-detect/explicit logic, the
`LLMClient.provider` public attribute, and every stub node-tag branch from
`spec/agent.md` -> "## Stub provider node-tag branching".
"""
import json

import pytest


def _reset_settings_env(monkeypatch, tmp_path, **keys):
    """Clear all provider env vars, then apply the given overrides; reset singleton."""
    monkeypatch.setenv("AGENT_DATABASE_URL", f"sqlite:///{tmp_path}/t.db")
    for var in (
        "AGENT_ANTHROPIC_API_KEY",
        "AGENT_GEMINI_API_KEY",
        "AGENT_OPENROUTER_API_KEY",
        "AGENT_LLM_PROVIDER",
        "AGENT_LLM_MODEL",
    ):
        monkeypatch.setenv(var, "")
    for var, value in keys.items():
        monkeypatch.setenv(var, value)
    import config.settings as m
    m._settings = None


# ---------------------------------------------------------------------------
# Factory auto-detect / explicit selection
# ---------------------------------------------------------------------------

def test_no_key_resolves_to_stub(monkeypatch, tmp_path):
    _reset_settings_env(monkeypatch, tmp_path)
    from llm.client import _make_provider
    name, provider = _make_provider()
    assert name == "stub"
    assert provider.__class__.__name__ == "StubProvider"


def test_anthropic_key_autodetects_anthropic(monkeypatch, tmp_path):
    _reset_settings_env(monkeypatch, tmp_path, AGENT_ANTHROPIC_API_KEY="sk-ant-fake")
    from llm.client import _resolve_provider_name
    assert _resolve_provider_name() == "anthropic"


def test_gemini_key_autodetects_gemini(monkeypatch, tmp_path):
    _reset_settings_env(monkeypatch, tmp_path, AGENT_GEMINI_API_KEY="AIza-fake")
    from llm.client import _resolve_provider_name
    assert _resolve_provider_name() == "gemini"


def test_openrouter_key_autodetects_openrouter(monkeypatch, tmp_path):
    _reset_settings_env(monkeypatch, tmp_path, AGENT_OPENROUTER_API_KEY="or-fake")
    from llm.client import _resolve_provider_name
    assert _resolve_provider_name() == "openrouter"


def test_autodetect_priority_anthropic_over_gemini(monkeypatch, tmp_path):
    _reset_settings_env(
        monkeypatch, tmp_path,
        AGENT_ANTHROPIC_API_KEY="sk-ant-fake",
        AGENT_GEMINI_API_KEY="AIza-fake",
        AGENT_OPENROUTER_API_KEY="or-fake",
    )
    from llm.client import _resolve_provider_name
    assert _resolve_provider_name() == "anthropic"


def test_autodetect_priority_gemini_over_openrouter(monkeypatch, tmp_path):
    _reset_settings_env(
        monkeypatch, tmp_path,
        AGENT_GEMINI_API_KEY="AIza-fake",
        AGENT_OPENROUTER_API_KEY="or-fake",
    )
    from llm.client import _resolve_provider_name
    assert _resolve_provider_name() == "gemini"


def test_explicit_stub_always_wins(monkeypatch, tmp_path):
    # Keys present, but explicit stub overrides auto-detect.
    _reset_settings_env(
        monkeypatch, tmp_path,
        AGENT_GEMINI_API_KEY="AIza-fake",
        AGENT_LLM_PROVIDER="stub",
    )
    from llm.client import _make_provider
    name, provider = _make_provider()
    assert name == "stub"
    assert provider.__class__.__name__ == "StubProvider"


def test_explicit_openrouter_selected(monkeypatch, tmp_path):
    _reset_settings_env(
        monkeypatch, tmp_path,
        AGENT_OPENROUTER_API_KEY="or-fake",
        AGENT_LLM_PROVIDER="openrouter",
    )
    from llm.client import _make_provider
    name, provider = _make_provider()
    assert name == "openrouter"
    assert provider.__class__.__name__ == "OpenRouterProvider"


def test_unknown_provider_raises(monkeypatch, tmp_path):
    _reset_settings_env(monkeypatch, tmp_path, AGENT_LLM_PROVIDER="bogus")
    from llm.client import _make_provider
    with pytest.raises(RuntimeError, match="Unknown LLM provider"):
        _make_provider()


# ---------------------------------------------------------------------------
# LLMClient.provider public attribute
# ---------------------------------------------------------------------------

def test_client_exposes_stub_provider_name(monkeypatch, tmp_path):
    _reset_settings_env(monkeypatch, tmp_path)  # no key -> stub
    from llm.client import LLMClient
    client = LLMClient()
    assert client.provider == "stub"


def test_client_exposes_resolved_provider_name(monkeypatch, tmp_path):
    _reset_settings_env(monkeypatch, tmp_path, AGENT_LLM_PROVIDER="stub")
    from llm.client import LLMClient
    assert LLMClient().provider == "stub"


def test_client_call_model_routes_through_stub(monkeypatch, tmp_path):
    _reset_settings_env(monkeypatch, tmp_path)  # no key -> stub
    from llm.client import LLMClient
    client = LLMClient()
    out = client.call_model("<node:clarify> Is this clear?")
    assert out == "proceed"


# ---------------------------------------------------------------------------
# Stub node-tag branches
# ---------------------------------------------------------------------------

@pytest.fixture
def stub():
    from llm.providers.stub import StubProvider
    return StubProvider()


def test_stub_constructor_tolerates_kwargs():
    from llm.providers.stub import StubProvider
    # Factory may pass api_key/model — must not error.
    StubProvider(api_key="anything", model="some-model")


def test_stub_finalize_returns_nonempty_summary(stub):
    out = stub.call_model("Synthesise the findings. <node:finalize>")
    assert isinstance(out, str)
    assert out.strip() != ""


def test_stub_select_returns_first_id_as_json_array(stub):
    prompt = (
        "<node:select>\n"
        "Schema block:\n"
        '  - id: abc-123  filename: sales.csv\n'
        '  - id: def-456  filename: returns.csv\n'
    )
    out = stub.call_model(prompt)
    parsed = json.loads(out)
    assert parsed == ["abc-123"]


def test_stub_select_returns_first_uuid(stub):
    prompt = (
        "<node:select> available datasets:\n"
        "11111111-2222-3333-4444-555555555555 (sales)\n"
        "99999999-8888-7777-6666-555555555555 (returns)\n"
    )
    out = stub.call_model(prompt)
    parsed = json.loads(out)
    assert parsed == ["11111111-2222-3333-4444-555555555555"]


def test_stub_select_empty_array_when_no_id(stub):
    out = stub.call_model("<node:select> there is nothing parseable here")
    assert json.loads(out) == []


def test_stub_plan_first_call_returns_describe_action(stub):
    # No Result:/Error: markers yet -> first call.
    prompt = "<node:plan>\nQuestion: what is the average price?\n"
    out = stub.call_model(prompt)
    assert out == "df.describe().to_string()"


def test_stub_plan_later_call_returns_final_answer(stub):
    # A Result: marker means at least one action ran -> wrap up.
    prompt = (
        "<node:plan>\nQuestion: what is the average price?\n"
        "Action: df.describe().to_string()\n"
        "Result: count 100 mean 42.0 ...\n"
    )
    out = stub.call_model(prompt)
    assert out.lower().startswith("final answer:")


def test_stub_plan_later_call_on_error_marker(stub):
    prompt = (
        "<node:plan>\nQuestion: what is the average price?\n"
        "Action: df.bogus()\n"
        "Error: AttributeError: no attribute bogus\n"
    )
    out = stub.call_model(prompt)
    assert out.lower().startswith("final answer:")


def test_stub_plan_first_and_later_differ_so_loop_terminates(stub):
    first = stub.call_model("<node:plan>\nQuestion: q\n")
    later = stub.call_model(
        "<node:plan>\nQuestion: q\nResult: something computed\n"
    )
    assert first != later


def test_stub_clarify_returns_proceed(stub):
    out = stub.call_model("<node:clarify> Should we ask for more detail?")
    assert out == "proceed"


def test_stub_suggest_returns_empty_array(stub):
    out = stub.call_model("<node:suggest> propose follow-ups")
    assert json.loads(out) == []


def test_stub_no_tag_returns_safe_default(stub):
    out = stub.call_model("just some prose with no node tag at all")
    assert out == "FINAL ANSWER: [stub] Unable to process"


def test_stub_branches_only_on_tag_not_prose(stub):
    # Prose mentions 'select' and 'plan' but the only injected tag is finalize.
    prose_prompt = (
        "Please select and plan and clarify the dataset. <node:finalize>"
    )
    finalize_only = stub.call_model("<node:finalize>")
    # The prose words must NOT change the branch — output equals the pure
    # finalize output (not the select JSON array, plan action, or 'proceed').
    assert stub.call_model(prose_prompt) == finalize_only
    assert finalize_only != "proceed"
    assert finalize_only != "df.describe().to_string()"


# ---------------------------------------------------------------------------
# Real token metering — complete() / LLMResponse
# ---------------------------------------------------------------------------

def test_stub_complete_returns_text_and_positive_usage(stub):
    # The stub has no real provider, so it reports a chars/4 estimate (>0), and
    # its text equals call_model's output for the same prompt.
    prompt = "<node:plan>\nQuestion: what is the average price?\n"
    system = "You are a data analyst."
    resp = stub.complete(prompt, system=system)
    assert resp.text == stub.call_model(prompt, system=system)
    assert resp.tokens_input > 0
    assert resp.tokens_output > 0
    # Input estimate accounts for both the prompt and the system instruction.
    assert resp.tokens_input >= max(1, len(prompt) // 4)


def test_client_complete_returns_llmresponse_in_stub_mode(monkeypatch, tmp_path):
    _reset_settings_env(monkeypatch, tmp_path)  # no key -> stub
    from llm.client import LLMClient
    from llm.providers.base import LLMResponse
    resp = LLMClient().complete("<node:clarify> clear?")
    assert isinstance(resp, LLMResponse)
    assert resp.text == "proceed"
    assert resp.tokens_input > 0 and resp.tokens_output > 0


def test_client_complete_passes_provider_usage_through_unchanged(monkeypatch, tmp_path):
    """A provider's REAL token counts must propagate verbatim — not be re-estimated."""
    _reset_settings_env(monkeypatch, tmp_path)
    from llm.client import LLMClient
    from llm.providers.base import LLMResponse

    class _FakeProvider:
        def complete(self, prompt, *, system=None):
            return LLMResponse("real answer", 1234, 56)

        def call_model(self, prompt, *, system=None):
            return self.complete(prompt, system=system).text

    client = LLMClient()
    client._provider = _FakeProvider()  # swap in a provider with known real usage
    resp = client.complete("anything")
    assert (resp.text, resp.tokens_input, resp.tokens_output) == ("real answer", 1234, 56)
