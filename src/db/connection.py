import os

import duckdb

from src.config import settings


def get_db() -> duckdb.DuckDBPyConnection:
    os.makedirs(os.path.dirname(settings.analyst_db_path), exist_ok=True)
    return duckdb.connect(settings.analyst_db_path)
