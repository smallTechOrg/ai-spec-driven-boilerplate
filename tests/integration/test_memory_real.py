"""Real-Gemini integration test for `/memory` (slice-3c, C31 compression).

Requires `AGENT_GEMINI_API_KEY` in `.env`. Auto-detect selects the real Gemini
provider (no key is forced to stub here). Drives GET -> PATCH -> GET through a
TestClient over a minimal app mounting the memory router, and asserts on REAL
content: PATCH returns a NON-EMPTY list of compressed facts derived by real
Gemini (a tolerant contains-check proves the real C31 extraction ran), and
`get_memory_block()` renders the stored memory text.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


_MEMORY_TEXT = (
    "Our fiscal year starts in April. Revenue is reported in GBP. "
    "The North region includes Scotland."
)


@pytest.fixture
def memory_client(_isolated_db):
    """TestClient over a minimal app mounting ONLY the memory router."""
    from api.memory import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        yield client


@pytest.mark.usefixtures("_require_llm_key")
def test_get_memory_empty_then_patch_compresses(memory_client):
    # 1) GET initially empty, always 200.
    g0 = memory_client.get("/memory")
    assert g0.status_code == 200, g0.text
    d0 = g0.json()["data"]
    assert d0["global_memory"] == ""
    assert d0["global_memory_facts"] == []

    # 2) PATCH with substantive memory -> real C31 compression.
    p = memory_client.patch("/memory", json={"global_memory": _MEMORY_TEXT})
    assert p.status_code == 200, p.text
    pd = p.json()["data"]
    assert pd["global_memory"] == _MEMORY_TEXT

    facts = pd["global_memory_facts"]
    assert isinstance(facts, list)
    assert 1 <= len(facts) <= 20, f"expected 1..20 real facts, got {facts!r}"
    assert all(isinstance(f, str) and f.strip() for f in facts)

    # Tolerant contains-check: real Gemini should capture at least one real fact
    # from the memory text (April / GBP / Scotland). Proves real extraction ran.
    joined = " ".join(facts).lower()
    assert any(k in joined for k in ("april", "gbp", "scotland")), (
        f"compressed facts did not capture a real fact from the memory: {facts!r}"
    )

    # 3) GET after PATCH reflects the new text + the compressed facts.
    g1 = memory_client.get("/memory").json()["data"]
    assert g1["global_memory"] == _MEMORY_TEXT
    assert g1["char_count"] == len(_MEMORY_TEXT)
    assert g1["global_memory_facts"] == facts
    assert g1["fact_count"] == len(facts)


@pytest.mark.usefixtures("_require_llm_key")
def test_patch_invalid_body_400(memory_client):
    r = memory_client.patch("/memory", json={"global_memory": 123})
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["code"] == "invalid_body"

    r2 = memory_client.patch("/memory", json={})
    assert r2.status_code == 400
    assert r2.json()["detail"]["code"] == "invalid_body"


@pytest.mark.usefixtures("_require_llm_key")
def test_memory_block_after_patch_contains_text(memory_client):
    """`get_memory_block()` (imported by slice-3b's plan_action) renders the text."""
    from graph.memory import get_memory_block

    memory_client.patch("/memory", json={"global_memory": _MEMORY_TEXT})

    block = get_memory_block()
    assert block, "memory block must be non-empty after a PATCH"
    assert _MEMORY_TEXT in block
    assert "authoritative" in block.lower()
