"""Phase-1 fixtures: isolated SQLite DB (from root conftest) + temp data dir.

The root ``tests/conftest.py`` already provides ``_isolated_db`` (autouse) and the
settings-singleton reset. Here we additionally redirect the dataset store's local
data root to a temp directory so uploads never touch the real ``data/`` tree.
"""

import io

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path, monkeypatch):
    """Point datasets.store at a temp data root so raw CSVs land in tmp_path."""
    import datasets.store as store_module

    data_root = tmp_path / "data"
    (data_root / "datasets").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(store_module, "_data_root", lambda: data_root)
    yield data_root


def _make_sales_df() -> pd.DataFrame:
    """Deterministic ≥200-row sales frame with ≥5 regions and a numeric revenue.

    Revenue per region is engineered so a full-data total differs from any small
    sample — the West region has the highest TOTAL revenue despite not always the
    highest individual values.
    """
    regions = ["North", "South", "East", "West", "Central", "Mountain"]
    rows = []
    for i in range(240):
        region = regions[i % len(regions)]
        # West gets a steady, large contribution so its total dominates.
        if region == "West":
            revenue = 500.0 + (i % 7) * 3.0
        else:
            revenue = 50.0 + (i % 11) * 2.0
        rows.append(
            {
                "region": region,
                "revenue": round(revenue, 2),
                "units": (i % 9) + 1,
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture
def sales_csv_bytes() -> bytes:
    """A valid sales CSV as raw bytes (≥200 rows, ≥5 regions, numeric revenue)."""
    df = _make_sales_df()
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


@pytest.fixture
def sales_df() -> pd.DataFrame:
    return _make_sales_df()
