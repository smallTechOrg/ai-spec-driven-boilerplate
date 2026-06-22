import uuid
import pytest
import aiosqlite
import datetime
from httpx import AsyncClient, ASGITransport
import src.api.main as main_mod
from src.db.sqlite import create_tables_sqlite


@pytest.fixture
async def client(tmp_path, monkeypatch):
    from src.config import get_settings
    monkeypatch.setenv("DAA_SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("DAA_DUCKDB_PATH", str(tmp_path / "test.duckdb"))
    get_settings.cache_clear()
    from src.api.main import create_app
    app = create_app()
    await create_tables_sqlite()
    main_mod._ready = True
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    main_mod._ready = False
    get_settings.cache_clear()


async def _create_session_and_dataset(sqlite_path: str, duckdb_path: str):
    """Helper: insert session + dataset rows directly (avoids endpoint dependency)."""
    import duckdb
    session_id = str(uuid.uuid4())
    dataset_id = str(uuid.uuid4())
    table_name = f"dataset_{dataset_id.replace('-', '_')}"
    now = datetime.datetime.now(datetime.UTC).isoformat()
    async with aiosqlite.connect(sqlite_path) as db:
        await db.execute(
            "INSERT INTO session (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (session_id, "Test", now, now),
        )
        await db.execute(
            "INSERT INTO dataset (id, session_id, name, file_format, row_count, column_names, duckdb_table, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (dataset_id, session_id, "sample.csv", "csv", 100, '["product","revenue","category"]', table_name, now),
        )
        await db.commit()
    # Create DuckDB table too
    con = duckdb.connect(duckdb_path)
    con.execute(f"CREATE OR REPLACE TABLE {table_name} (product VARCHAR, revenue DOUBLE, category VARCHAR)")
    con.close()
    return session_id, dataset_id


@pytest.mark.asyncio
async def test_stub_query(client, tmp_path):
    """P1-AC3: POST /query stub returns 200, rows[0].product==Widget A, sql starts SELECT, chart_spec.xaxis.title==product."""
    from src.config import get_settings
    session_id, dataset_id = await _create_session_and_dataset(
        get_settings().sqlite_path, get_settings().duckdb_path
    )
    r = await client.post("/query", json={
        "session_id": session_id,
        "dataset_ids": [dataset_id],
        "question": "What are the top 5 products by revenue?",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["rows"]) == 5
    assert body["rows"][0]["product"] == "Widget A"
    assert body["sql"].upper().startswith("SELECT")
    assert body["chart_spec"]["layout"]["xaxis"]["title"] == "product"
    assert len(body["suggestions"]) >= 2


@pytest.mark.asyncio
async def test_empty_question(client, tmp_path):
    """P1-AC9: empty question → 422 BAD_INPUT."""
    from src.config import get_settings
    session_id, dataset_id = await _create_session_and_dataset(
        get_settings().sqlite_path, get_settings().duckdb_path
    )
    r = await client.post("/query", json={
        "session_id": session_id,
        "dataset_ids": [dataset_id],
        "question": "",
    })
    assert r.status_code == 422
    assert r.json()["detail"]["error"]["code"] == "BAD_INPUT"


@pytest.mark.asyncio
async def test_invalid_session(client):
    """Missing session → 404 NO_SESSION."""
    r = await client.post("/query", json={
        "session_id": str(uuid.uuid4()),
        "dataset_ids": [],
        "question": "test",
    })
    assert r.status_code == 404
    assert r.json()["detail"]["error"]["code"] == "NO_SESSION"
