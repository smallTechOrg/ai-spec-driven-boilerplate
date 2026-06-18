"""API tests — dataset CRUD + upload (no LLM) and the golden-path query (real Gemini)."""

from __future__ import annotations

import json
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import datachat.db.session as db_session_module
from datachat.api import create_app
from datachat.data import engine
from datachat.db.models import Base

CSV = b"region,product,sales\nwest,widget,100\neast,widget,200\nwest,gadget,50\neast,gadget,75\n"

_HAS_KEY = bool(
    os.environ.get("DATA_ANALYST_GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
)


@pytest_asyncio.fixture
async def client(db_engine, monkeypatch):
    # Point the app's sessionmaker at the test engine (same file-backed test DB).
    from sqlalchemy.ext.asyncio import async_sessionmaker

    maker = async_sessionmaker(db_engine, expire_on_commit=False)
    monkeypatch.setattr(db_session_module, "_sessionmaker", maker)
    monkeypatch.setattr(db_session_module, "_engine", db_engine)

    async def _noop():  # init_db is async — replace with an async noop, not a sync lambda
        return None

    monkeypatch.setattr("datachat.api.init_db", _noop)

    app = create_app()
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_dataset_create_and_upload(client):
    r = await client.post("/datasets", json={"name": "Q1"})
    assert r.status_code == 201
    dataset_id = r.json()["data"]["id"]

    files = {"files": ("sales.csv", CSV, "text/csv")}
    r = await client.post(f"/datasets/{dataset_id}/files", files=files)
    assert r.status_code == 201, r.text
    body = r.json()["data"]
    assert body["files"][0]["row_count"] == 4
    cols = {c["name"] for c in body["files"][0]["schema_columns"]}
    assert cols == {"region", "product", "sales"}

    engine.release(dataset_id)


@pytest.mark.asyncio
async def test_bad_csv_returns_clean_error(client):
    r = await client.post("/datasets", json={"name": "bad"})
    dataset_id = r.json()["data"]["id"]
    files = {"files": ("empty.csv", b"", "text/csv")}
    r = await client.post(f"/datasets/{dataset_id}/files", files=files)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "BAD_CSV"


@pytest.mark.skipif(not _HAS_KEY, reason="Real Gemini key not set.")
@pytest.mark.asyncio
async def test_golden_path_query_sse(client):
    r = await client.post("/datasets", json={"name": "sales"})
    dataset_id = r.json()["data"]["id"]
    await client.post(
        f"/datasets/{dataset_id}/files",
        files={"files": ("sales.csv", CSV, "text/csv")},
    )
    r = await client.post("/conversations", json={"dataset_id": dataset_id})
    conv_id = r.json()["data"]["id"]

    events: list[tuple[str, dict]] = []
    async with client.stream(
        "POST", f"/conversations/{conv_id}/query",
        json={"question": "What is the total of all sales?"},
    ) as resp:
        assert resp.status_code == 200
        event = None
        async for line in resp.aiter_lines():
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and event:
                events.append((event, json.loads(line.split(":", 1)[1].strip())))

    kinds = {e for e, _ in events}
    assert "answer" in kinds and "done" in kinds
    answer = next(d for e, d in events if e == "answer")
    assert answer["content"].strip()
    haystack = answer["content"] + json.dumps(answer.get("result_table") or {})
    assert "425" in haystack

    # Multi-turn: a follow-up question on the same conversation works.
    async with client.stream(
        "POST", f"/conversations/{conv_id}/query",
        json={"question": "Now show only the west region's total."},
    ) as resp:
        assert resp.status_code == 200
        saw_answer = False
        ev = None
        async for line in resp.aiter_lines():
            if line.startswith("event:"):
                ev = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and ev == "answer":
                saw_answer = True
    assert saw_answer

    r = await client.get(f"/conversations/{conv_id}")
    msgs = r.json()["data"]["messages"]
    assert len([m for m in msgs if m["role"] == "user"]) == 2

    engine.release(dataset_id)
