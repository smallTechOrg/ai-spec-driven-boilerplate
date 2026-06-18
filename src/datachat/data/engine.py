"""DuckDB analytical engine — session-scoped per dataset (module-level store).

The DuckDB connection holding a dataset's tables is a **session-scoped resource**
(patterns/react-agent.md § Resource lifecycle): kept in a module-level store keyed by
`dataset_id`, shared across runs in the same conversation, and released only when the
dataset is deleted — never in terminal graph nodes.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

import duckdb

_STORE_DIR = Path(os.environ.get("DATA_ANALYST_DUCKDB_DIR", ".duckdb_store"))

_engines: dict[str, duckdb.DuckDBPyConnection] = {}
_lock = threading.Lock()


def db_path(dataset_id: str) -> Path:
    """Each dataset is a file-backed DuckDB so a separate MCP process can open it too."""
    _STORE_DIR.mkdir(parents=True, exist_ok=True)
    return _STORE_DIR / f"{dataset_id}.duckdb"


def get_connection(dataset_id: str) -> duckdb.DuckDBPyConnection:
    """Return the dataset's DuckDB connection (file-backed), creating it on first use."""
    with _lock:
        conn = _engines.get(dataset_id)
        if conn is None:
            conn = duckdb.connect(database=str(db_path(dataset_id)))
            _engines[dataset_id] = conn
        return conn


def has_connection(dataset_id: str) -> bool:
    """True if the dataset's DuckDB file exists (its tables can be queried)."""
    with _lock:
        if dataset_id in _engines:
            return True
    return db_path(dataset_id).exists()


def release(dataset_id: str) -> None:
    """Drop the dataset's DuckDB connection + file. Call only on dataset deletion."""
    with _lock:
        conn = _engines.pop(dataset_id, None)
    if conn is not None:
        conn.close()
    path = db_path(dataset_id)
    if path.exists():
        path.unlink()


def list_tables(dataset_id: str) -> list[str]:
    conn = get_connection(dataset_id)
    rows = conn.execute("SHOW TABLES").fetchall()
    return [r[0] for r in rows]
