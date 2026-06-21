"""DuckDB event-store seam — THE storage layer that makes this recipe differ from
python-fastapi-sqlite.

A tiny, generic columnar event log: one ``events`` table (created at bootstrap),
``append_event`` to write one row, ``read_events`` to read them back. The echo
example writes one event here purely to demonstrate the DuckDB storage seam — there
is no file upload, no SQL generation, and no schema introspection.

[REPLACE ME] Swap this seam for whatever analytical / columnar workload your agent
needs (aggregations, time-series, large scans). Keep the read/write split if you
later expose any read path to the agent.
"""

import datetime as dt
import os

import duckdb

from src.config import get_settings


def _db_path() -> str:
    data_dir = get_settings().data_dir
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "events.duckdb")


def init_event_store() -> None:
    """Create the single columnar ``events`` table if it does not exist."""
    con = duckdb.connect(_db_path())
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS events ("
            "  id BIGINT PRIMARY KEY,"
            "  kind VARCHAR,"
            "  payload VARCHAR,"
            "  created_at TIMESTAMP"
            ")"
        )
    finally:
        con.close()


def append_event(kind: str, payload: str) -> int:
    """Append one event row and return its id. Auto-increments off the current max id."""
    init_event_store()  # idempotent — ensures the table exists if bootstrap was skipped
    con = duckdb.connect(_db_path())
    try:
        next_id = (con.execute("SELECT coalesce(max(id), 0) + 1 FROM events").fetchone() or [1])[0]
        con.execute(
            "INSERT INTO events (id, kind, payload, created_at) VALUES (?, ?, ?, ?)",
            [next_id, kind, payload, dt.datetime.now(dt.UTC)],
        )
        return int(next_id)
    finally:
        con.close()


def read_events(limit: int = 50) -> list[dict]:
    """Read back the most recent events (newest first)."""
    con = duckdb.connect(_db_path(), read_only=True)
    try:
        rows = con.execute(
            "SELECT id, kind, payload, created_at FROM events ORDER BY id DESC LIMIT ?",
            [limit],
        ).fetchall()
        return [
            {"id": r[0], "kind": r[1], "payload": r[2], "created_at": str(r[3])} for r in rows
        ]
    finally:
        con.close()
