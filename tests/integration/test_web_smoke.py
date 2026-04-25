"""Golden-path UI smoke test.

Walks the full primary user journey via TestClient and asserts response
content (not just status codes), per
spec/engineering/workflows/golden-path-smoke-test.md and
spec/engineering/ai-agents.md rule 6.
"""
from __future__ import annotations

from fastapi.testclient import TestClient


def _client():
    from sourcing_agent.api import create_app

    return TestClient(create_app())


def test_health_returns_ok():
    r = _client().get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_form_page_renders_with_stub_banner():
    r = _client().get("/")
    assert r.status_code == 200
    body = r.text
    assert "New sourcing request" in body
    assert "Find suppliers" in body
    # Stub banner must be visible (no API keys set in test env)
    assert "Demo / stub mode" in body
    assert "LLM=<code>stub</code>" in body or "stub</code>" in body


def test_full_user_journey_form_submit_to_report():
    client = _client()

    # 1. Form loads
    r1 = client.get("/")
    assert r1.status_code == 200
    assert "Find suppliers" in r1.text

    # 2. Submit a request — TestClient follows the 303 redirect to /runs/{id}
    r2 = client.post(
        "/requests",
        data={
            "material": "red clay brick",
            "quantity": "10000 units",
            "location": "Bangalore",
            "budget": "₹70,000",
            "timeline": "2 weeks",
            "criteria": "ISI-marked preferred",
        },
        follow_redirects=True,
    )
    assert r2.status_code == 200
    body = r2.text

    # Report content assertions — not just status code
    assert "Sourcing report" in body
    assert "completed" in body
    assert "red clay brick" in body
    assert "Bangalore" in body
    assert "Recommendations" in body
    # At least one ranked recommendation rendered
    assert "#1" in body
    # Score rendered
    assert "/100" in body
    # Stub banner still on report page
    assert "Demo / stub mode" in body

    # 3. Recent-runs list shows the new run
    r3 = client.get("/runs")
    assert r3.status_code == 200
    assert "red clay brick" in r3.text
    assert "completed" in r3.text


def test_stub_llm_branches_on_node_tags_only():
    """Stub must not cross-contaminate: an enrich prompt and a score prompt
    must produce different shapes, driven by their <node:...> tags."""
    from sourcing_agent.llm.stub import StubLLMProvider

    enrich_prompt = (
        "<node:enrich>\nmaterial=brick\n<results>"
        '[{"name":"Acme","location":"Bangalore","url":"https://x"}]</results>'
    )
    score_prompt = (
        "<node:score>\nmaterial=brick\n<results>"
        '[{"name":"Acme","location":"Bangalore","price_indication":"x","lead_time":"y"}]'
        "</results>"
    )
    enrich_out = StubLLMProvider().complete(enrich_prompt)
    score_out = StubLLMProvider().complete(score_prompt)

    assert "price_indication" in enrich_out
    assert "rationale" in score_out
    assert "score" in score_out
    # No cross-contamination: enrich output has no "score" field
    import json
    assert all("score" not in item for item in json.loads(enrich_out))
