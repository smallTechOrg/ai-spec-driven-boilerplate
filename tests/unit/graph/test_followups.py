"""Follow-ups node unit tests — parser, privacy, and degradation.

No LLM key required: these patch the client or test pure functions.
"""
import graph.nodes as nodes
from llm.client import LLMClient as _RealLLMClient


def _fake_client_factory(provider):
    def _factory():
        c = object.__new__(_RealLLMClient)
        c._provider = provider
        return c
    return _factory


SECRET_VALUE = "TOP_SECRET_PII_ROW_99441"


def _state():
    # 20 allowed sample rows + a question + an answer. A secret value lives only
    # in sample-beyond contexts and must NOT reach the follow-ups prompt.
    return {
        "run_id": "fu",
        "question": "How many orders per status?",
        "schema": [
            {"name": "order_status", "dtype": "object"},
            {"name": "price", "dtype": "float64"},
        ],
        "sample_rows": [{"order_status": "delivered", "price": 9.9, "pii": SECRET_VALUE}],
        "answer": "There are 5 statuses; delivered is the largest at 96478.",
        "tokens": 0,
    }


# --- parser ----------------------------------------------------------------

def test_parse_followups_json_array():
    out = nodes._parse_followups('["What is X?", "What is Y?", "What is Z?"]')
    assert out == ["What is X?", "What is Y?", "What is Z?"]


def test_parse_followups_fenced_json():
    text = '```json\n["A?", "B?"]\n```'
    assert nodes._parse_followups(text) == ["A?", "B?"]


def test_parse_followups_line_fallback():
    text = "- First question?\n- Second question?\n- Third question?"
    out = nodes._parse_followups(text)
    assert out == ["First question?", "Second question?", "Third question?"]


def test_parse_followups_caps_at_three():
    out = nodes._parse_followups('["a?","b?","c?","d?","e?"]')
    assert len(out) == 3


def test_parse_followups_empty():
    assert nodes._parse_followups("") == []
    assert nodes._parse_followups("   ") == []


# --- privacy ---------------------------------------------------------------

def test_followups_prompt_is_schema_only():
    """The follow-ups prompt carries schema + question + short answer ONLY —
    never sample rows or full data (HARD privacy constraint)."""
    prompt = nodes.build_followups_prompt(_state())
    assert "order_status" in prompt          # schema present
    assert "How many orders per status?" in prompt  # question present
    assert SECRET_VALUE not in prompt        # no sample/full-file PII leaks


def test_suggest_followups_node_prompt_excludes_full_data(monkeypatch):
    captured = {}

    class _Capture:
        def call_model_with_usage(self, prompt, *, system=None):
            captured["prompt"] = prompt
            captured["system"] = system
            return '["A?", "B?"]', 4

    monkeypatch.setattr(nodes, "LLMClient", _fake_client_factory(_Capture()))
    out = nodes.suggest_followups(_state())
    assert out["followups"] == ["A?", "B?"]
    assert SECRET_VALUE not in captured["prompt"]
    assert out["tokens"] == 4


# --- degradation -----------------------------------------------------------

def test_suggest_followups_degrades_on_llm_failure(monkeypatch):
    class _Boom:
        def call_model_with_usage(self, prompt, *, system=None):
            raise RuntimeError("gemini down")

    monkeypatch.setattr(nodes, "LLMClient", _fake_client_factory(_Boom()))
    out = nodes.suggest_followups(_state())
    assert out["followups"] == []  # run still completes


def test_suggest_followups_degrades_on_unparseable(monkeypatch):
    class _Junk:
        def call_model_with_usage(self, prompt, *, system=None):
            return "", 1

    monkeypatch.setattr(nodes, "LLMClient", _fake_client_factory(_Junk()))
    out = nodes.suggest_followups(_state())
    assert out["followups"] == []
