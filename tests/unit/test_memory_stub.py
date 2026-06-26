"""Offline unit suite for the `/memory` routes + the memory helpers (slice-3c).

Stub provider + in-memory SQLite (via conftest's `_isolated_db`), zero network.
Exercises the GET/PATCH envelope + status codes, that PATCH stores the text, and
that `get_memory_block()` renders the memory text block. In stub mode the
compression LLM call hits the stub provider, which has no `<node:compress>`
branch, so `compress_memory` parses a non-JSON reply and returns [] BY DESIGN —
the facts come back empty offline. The real C31 extraction is proven in
`tests/integration/test_memory_real.py` against real Gemini.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _force_stub_provider(monkeypatch):
    """Pin the offline stub provider regardless of any key in `.env`."""
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "stub")
    import config.settings as m
    m._settings = None


@pytest.fixture
def memory_client(_isolated_db):
    """A TestClient over a minimal app that mounts ONLY the memory router.

    Slice-3a registers `memory.router` in `api/__init__.py`; this suite owns only
    the memory surface, so it builds its own app to stay self-contained and
    disjoint from the other slices.
    """
    from api.memory import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        yield client


# --- GET /memory ---------------------------------------------------------


def test_get_memory_initially_empty(memory_client):
    r = memory_client.get("/memory")
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["global_memory"] == ""
    assert data["global_memory_facts"] == []
    assert data["char_count"] == 0
    assert data["fact_count"] == 0


# --- PATCH /memory (valid body) -----------------------------------------


def test_patch_memory_stores_text(memory_client):
    text = "Revenue is reported in GBP. The fiscal year starts in April."
    r = memory_client.patch("/memory", json={"global_memory": text})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["global_memory"] == text
    # Stub mode: no <node:compress> branch -> non-JSON reply -> [] by design.
    assert data["global_memory_facts"] == []

    # GET reflects the stored text.
    g = memory_client.get("/memory").json()["data"]
    assert g["global_memory"] == text
    assert g["char_count"] == len(text)
    assert g["global_memory_facts"] == []


def test_patch_memory_empty_string_clears(memory_client):
    memory_client.patch("/memory", json={"global_memory": "something"})
    r = memory_client.patch("/memory", json={"global_memory": ""})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["global_memory"] == ""
    assert memory_client.get("/memory").json()["data"]["global_memory"] == ""


# --- PATCH /memory (invalid body -> 400 invalid_body) -------------------


@pytest.mark.parametrize(
    "bad_body",
    [
        {"global_memory": 123},     # number, not a string
        {"global_memory": None},    # null
        {"global_memory": True},    # bool
        {"global_memory": ["a"]},   # list
        {},                         # missing field
    ],
)
def test_patch_memory_invalid_body_400(memory_client, bad_body):
    r = memory_client.patch("/memory", json=bad_body)
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["code"] == "invalid_body"


def test_patch_memory_non_json_body_400(memory_client):
    r = memory_client.patch(
        "/memory",
        content=b"not json",
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "invalid_body"


# --- get_memory_block() (imported directly by slice-3b's plan_action) ----


def test_memory_block_empty_when_nothing_set(_isolated_db):
    from graph.memory import get_memory_block

    assert get_memory_block() == ""


def test_memory_block_contains_text_when_set(_isolated_db):
    from graph.memory import get_memory_block, set_memory_text

    text = "The North region includes Scotland."
    set_memory_text(text)
    block = get_memory_block()
    assert block != ""
    assert text in block
    assert "authoritative" in block.lower()


def test_memory_block_renders_facts_when_set(_isolated_db):
    from graph.memory import get_memory_block, set_memory_facts, set_memory_text

    set_memory_text("Sales context.")
    set_memory_facts(["Revenue is in GBP", "FY starts in April"])
    block = get_memory_block()
    assert "Key facts:" in block
    assert "- Revenue is in GBP" in block
    assert "- FY starts in April" in block


def test_memory_block_never_raises_on_db_error(monkeypatch):
    """get_memory_block must swallow any error (it runs every iteration)."""
    import graph.memory as mem

    def _boom(*_a, **_k):
        raise RuntimeError("db down")

    monkeypatch.setattr(mem, "get_memory_text", _boom)
    assert mem.get_memory_block() == ""


# --- helper read/write round-trips --------------------------------------


def test_set_and_get_memory_facts_roundtrip(_isolated_db):
    from graph.memory import get_memory_facts, set_memory_facts

    assert get_memory_facts() == []
    set_memory_facts(["a", "b", "c"])
    assert get_memory_facts() == ["a", "b", "c"]


def test_set_memory_facts_caps_at_20(_isolated_db):
    from graph.memory import get_memory_facts, set_memory_facts

    set_memory_facts([f"fact {i}" for i in range(50)])
    assert len(get_memory_facts()) == 20


def test_compress_memory_returns_empty_in_stub_mode(_isolated_db):
    """Stub provider has no <node:compress> branch -> non-JSON -> [] by design."""
    from graph.memory import compress_memory

    facts = compress_memory("Revenue is reported in GBP. FY starts in April.")
    assert facts == []


def test_compress_memory_empty_text_returns_empty(_isolated_db):
    from graph.memory import compress_memory

    assert compress_memory("") == []
    assert compress_memory("   ") == []
