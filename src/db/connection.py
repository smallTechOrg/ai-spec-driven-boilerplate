import os

import duckdb

from src.config import settings
from src.db.schema import create_tables


def get_db() -> duckdb.DuckDBPyConnection:
    dirname = os.path.dirname(settings.analyst_db_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    return duckdb.connect(settings.analyst_db_path)


def init_db() -> None:
    conn = get_db()
    create_tables(conn)
    conn.close()
