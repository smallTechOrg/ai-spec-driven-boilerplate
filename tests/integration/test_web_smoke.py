"""Golden-path UI smoke test per spec/engineering/workflows/golden-path-smoke-test.md.

Walks the full primary user journey and asserts rendered content, not just 200.
No GEMINI_API_KEY required — stub mode.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from lead_gen_agent.api import create_app


def test_golden_path_home_run_leads_csv():
    client = TestClient(create_app())

    # 1. Home renders with banner + form
    r = client.get("/")
    assert r.status_code == 200
    assert "Lead Gen Agent" in r.text
    assert "Trigger a new run" in r.text
    assert "Stub LLM" in r.text, "stub-mode banner missing"
    assert 'name="country"' in r.text
    assert 'name="industry"' in r.text

    # 2. Health endpoint
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

    # 3. Trigger a run
    r = client.post(
        "/runs",
        data={"country": "Germany", "industry": "Manufacturing", "size_band": "11-50"},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text
    assert r.headers["location"] == "/runs"

    # 4. Runs page shows the completed run
    r = client.get("/runs")
    assert r.status_code == 200
    assert "Stub LLM" in r.text  # banner present on every page
    assert "completed" in r.text
    assert "Germany" in r.text

    # 5. Leads page shows ranked leads with content
    r = client.get("/leads")
    assert r.status_code == 200
    assert "Stub LLM" in r.text
    # Stub creates these exact names:
    assert "Müller Präzisionstechnik GmbH" in r.text
    assert "Nordlicht Logistik AG" in r.text
    assert "<strong>" in r.text  # score rendered bold
    assert "Download filtered CSV" in r.text
    assert len(r.text) > 800  # sanity

    # 6. CSV export
    r = client.get("/leads.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    body = r.text
    header_line, *data_lines = body.strip().splitlines()
    assert header_line.startswith("name,website,country,industry,size_band")
    assert len(data_lines) >= 1
    assert "Müller Präzisionstechnik GmbH" in body

    # 7. Filter by high min_score narrows the list
    r = client.get("/leads?min_score=101")
    assert r.status_code == 200
    assert "No leads match" in r.text
