"""Deterministic CSV fixtures for Phase 1 tests.

The skewed dataset is built so that a sample (first N rows) gives a DIFFERENT
aggregate from the full data — this lets the gate prove full-data execution, not
sampling.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_skewed_orders_csv(path: Path, n: int = 12000) -> dict:
    """Write a skewed orders CSV and return the ground-truth full-data answer.

    Region distribution and order_value are deliberately skewed by row position:
    the first rows are dominated by a low-value region, while later rows carry a
    high-value region — so a head() sample mis-estimates the per-region means.

    Returns {"path": str, "region_means": {region: mean_over_ALL_rows}}.
    """
    rows = []
    for i in range(n):
        # First 40% of rows: only "North" at low values. Remainder: skewed mix.
        if i < int(n * 0.4):
            region = "North"
            value = 10.0 + (i % 5)          # ~10-14
        elif i % 3 == 0:
            region = "West"
            value = 900.0 + (i % 50)         # high
        elif i % 3 == 1:
            region = "East"
            value = 300.0 + (i % 20)
        else:
            region = "North"
            value = 500.0 + (i % 30)         # raises North's TRUE mean far above sample
        rows.append({"region": region, "order_value": round(value, 2)})

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)

    region_means = {
        k: round(float(v), 4)
        for k, v in df.groupby("region")["order_value"].mean().to_dict().items()
    }
    return {"path": str(path), "region_means": region_means, "row_count": n}


def write_simple_csv(path: Path) -> Path:
    """A tiny well-typed CSV for profile-shape assertions."""
    df = pd.DataFrame(
        {
            "region": ["West", "East", "North", "West", None],
            "order_value": [120.5, 80.0, 200.0, None, 50.0],
            "qty": [1, 2, 3, 4, 5],
        }
    )
    df.to_csv(path, index=False)
    return path
