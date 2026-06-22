import uuid
import pytest
import aiosqlite
import datetime
import duckdb
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


@pytest.mark.asyncio
async def test_stub_llm_audit_row(client, tmp_path):
    """P1-AC8: POST /query stub writes exactly 1 audit_log row with action='llm' and duration_ms>=0."""
    from src.config import get_settings
    sqlite_path = get_settings().sqlite_path
    duckdb_path = get_settings().duckdb_path

    session_id = str(uuid.uuid4())
    dataset_id = str(uuid.uuid4())
    table_name = f"dataset_{dataset_id.replace('-', '_')}"
    now = datetime.datetime.now(datetime.UTC).isoformat()
    async with aiosqlite.connect(sqlite_path) as db:
        await db.execute(
            "INSERT INTO session (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (session_id, "AuditTest", now, now),
        )
        await db.execute(
            "INSERT INTO dataset (id, session_id, name, file_format, row_count, column_names, duckdb_table, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (dataset_id, session_id, "sample.csv", "csv", 100, '["product","revenue"]', table_name, now),
        )
        await db.commit()
    con = duckdb.connect(duckdb_path)
    con.execute(f"CREATE OR REPLACE TABLE {table_name} (product VARCHAR, revenue DOUBLE)")
    con.close()

    # Count before
    async with aiosqlite.connect(sqlite_path) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM audit_log WHERE action='llm'")
        count_before = (await cursor.fetchone())[0]

    r = await client.post("/query", json={
        "session_id": session_id,
        "dataset_ids": [dataset_id],
        "question": "What are the top 5 products?",
    })
    assert r.status_code == 200, r.text

    # Count after + check row
    async with aiosqlite.connect(sqlite_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT COUNT(*) FROM audit_log WHERE action='llm'")
        count_after = (await cursor.fetchone())[0]
        cursor = await db.execute(
            "SELECT * FROM audit_log WHERE action='llm' ORDER BY created_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()

    assert count_after - count_before == 1, f"Expected 1 new audit row, got {count_after - count_before}"
    assert row["duration_ms"] >= 0
    assert row["action"] == "llm"
