"""
Phase 2 integration test — golden-path smoke test.

Walks the full primary user flow via TestClient:
  GET / → GET /runs/new → POST /runs → GET /runs/{id} → GET /leads/export.csv

Uses the stub LLM provider (no API key required).
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lead_gen_agent.db.models import Base


def _get_db_url() -> str:
    url = os.environ.get("LGA_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("LGA_DATABASE_URL not set")
    return url


@pytest.fixture(scope="module")
def client(monkeypatch_module):
    """Return a TestClient with the stub LLM provider forced."""
    monkeypatch_module.setenv("LGA_LLM_PROVIDER", "stub")
    monkeypatch_module.setenv("LGA_GEMINI_API_KEY", "")
    monkeypatch_module.setenv(
        "LGA_DATABASE_URL", _get_db_url()
    )

    # Reset singleton caches so the patched env takes effect
    import lead_gen_agent.config as cfg
    from lead_gen_agent.db.session import reset_engine
    cfg._settings = None
    reset_engine()

    from lead_gen_agent.api import create_app
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    cfg._settings = None
    reset_engine()


@pytest.fixture(scope="module")
def monkeypatch_module(request):
    """Module-scoped monkeypatch (pytest only provides function scope by default)."""
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()


class TestGoldenPath:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_dashboard_loads(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Lead Dashboard" in resp.text
        # Stub banner must be visible
        assert "Stub mode" in resp.text

    def test_new_run_form_loads(self, client):
        resp = client.get("/runs/new")
        assert resp.status_code == 200
        assert "Find New Leads" in resp.text

    def test_create_run_and_redirect(self, client):
        resp = client.post(
            "/runs",
            data={"country": "DE", "industry": "retail", "size_min": "", "size_max": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        run_url = resp.headers["location"]
        assert run_url.startswith("/runs/")
        # Follow the redirect
        resp2 = client.get(run_url)
        assert resp2.status_code == 200
        assert "Run Results" in resp2.text
        # Leads must appear
        assert "Müller Logistik" in resp2.text or "GmbH" in resp2.text or "completed" in resp2.text

    def test_export_csv_returns_csv(self, client):
        resp = client.get("/leads/export.csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        # CSV must have a header row
        assert "company_name" in resp.text
