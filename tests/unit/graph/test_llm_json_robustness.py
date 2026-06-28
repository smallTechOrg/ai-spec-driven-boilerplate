"""LLM-JSON robustness for the planner/narrator (no live key required).

These tests pin the two-part hardening that keeps Phase 1 first-time-right on the
LIVE user path:

1. The JSON nodes request Gemini structured output (`response_mime_type=
   "application/json"`) so the model returns clean JSON, WITHOUT bypassing the
   privacy spy (which patches `LLMClient.call_model_usage(prompt, *, system=...)`).
2. A bounded PARSE-failure retry: if a response cannot be parsed into the
   expected pydantic model, the node retries a small fixed number of times before
   surfacing status="failed". Tokens accumulate across attempts.

They monkeypatch the provider boundary (not the LLMClient method the privacy spy
patches), so they are deterministic and need no API key.
"""
from __future__ import annotations

import graph.nodes as nodes
from domain.ask import Narration, Plan
from llm.providers.gemini import LLMResult


def _fake_provider_factory(responses):
    """A fake LLM provider that yields queued (text) responses in order.

    Mirrors the real provider boundary: `call_model_usage(prompt, *, system, ...)`
    returns an LLMResult with real-looking token counts. Accepts and records the
    `json_mode` flag so a test can assert structured output was requested.
    """
    calls = {"json_modes": [], "count": 0}

    class _FakeProvider:
        def __init__(self, *a, **k):
            self._json_mode = k.get("json_mode", False)

        def call_model_usage(self, prompt, *, system=None, json_mode=None):
            calls["json_modes"].append(
                self._json_mode if json_mode is None else json_mode
            )
            i = calls["count"]
            calls["count"] += 1
            text = responses[min(i, len(responses) - 1)]
            return LLMResult(text=text, prompt_tokens=11, completion_tokens=7)

        def call_model(self, prompt, *, system=None):  # pragma: no cover
            return self.call_model_usage(prompt, system=system).text

    return _FakeProvider, calls


def _state():
    return {
        "question": "totals by region?",
        "schema": [{"name": "region", "type": "VARCHAR"}],
        "profile": {"row_count": 3, "columns": []},
        "messages": [],
        "aggregates": {"row_count": 1, "table": {"columns": ["region"], "rows": [["W"]]}},
    }


def test_plan_recovers_from_one_malformed_json_response(monkeypatch):
    """First Gemini reply is malformed mid-object; a retry yields valid JSON.

    Without the parse-retry this raises and the run fails; with it the plan node
    succeeds and tokens from BOTH attempts are accumulated.
    """
    malformed = '{"steps": ["a", "b",  "sql": "SELECT region FROM ds"'  # missing ] / brace
    good = '{"steps": ["group by region"], "sql": "SELECT region FROM ds GROUP BY region"}'
    FakeProvider, calls = _fake_provider_factory([malformed, good])
    monkeypatch.setattr("llm.client._make_provider", lambda **k: FakeProvider(**k))

    out = nodes.plan(_state())

    assert "error" not in out or not out["error"], out.get("error")
    assert out["generated_sql"] == "SELECT region FROM ds GROUP BY region"
    assert calls["count"] == 2, "expected exactly one parse-retry"
    # tokens from BOTH attempts accumulate
    assert out["prompt_tokens"] == 22
    assert out["completion_tokens"] == 14


def test_plan_requests_json_mime_type(monkeypatch):
    """The JSON node asks the Gemini provider for application/json output."""
    good = '{"steps": ["s"], "sql": "SELECT 1 FROM ds"}'
    FakeProvider, calls = _fake_provider_factory([good])
    monkeypatch.setattr("llm.client._make_provider", lambda **k: FakeProvider(**k))

    nodes.plan(_state())

    assert calls["json_modes"], "provider was never called"
    assert all(calls["json_modes"]), "json_mode was not requested for the JSON node"


def test_plan_surfaces_failure_after_bounded_retries(monkeypatch):
    """Genuinely unrecoverable JSON still surfaces transparently as a failure.

    The node must NOT loop forever and must NOT fabricate a plan — it returns an
    error after a bounded number of attempts so the run ends status="failed".
    """
    garbage = "I'm sorry, I cannot help with that."
    FakeProvider, calls = _fake_provider_factory([garbage])
    monkeypatch.setattr("llm.client._make_provider", lambda **k: FakeProvider(**k))

    out = nodes.plan(_state())

    assert out.get("error"), "an unrecoverable response must surface as an error"
    assert "generated_sql" not in out or not out.get("generated_sql")
    # bounded: original attempt + the parse retries, no more.
    assert calls["count"] == nodes._MAX_PARSE_RETRIES + 1


def test_narrate_recovers_from_one_malformed_json_response(monkeypatch):
    malformed = '{"answer": "ok", "key_stats": ['  # truncated
    good = (
        '{"answer": "Region W leads.", "key_stats": [{"label": "regions", "value": 1}],'
        ' "chart_spec": {"type": "bar"}, "summary_table": {"columns": ["region"],'
        ' "rows": [["W"]]}, "insight": "W dominates."}'
    )
    FakeProvider, calls = _fake_provider_factory([malformed, good])
    monkeypatch.setattr("llm.client._make_provider", lambda **k: FakeProvider(**k))

    out = nodes.narrate(_state())

    assert "error" not in out or not out["error"], out.get("error")
    assert out["answer"] == "Region W leads."
    assert calls["count"] == 2
    assert all(calls["json_modes"])
