"""Real-Gemini E2E for inline Plotly chart capture (C4, slice-4a).

Requires `AGENT_GEMINI_API_KEY` in `.env` (auto-detect selects the real Gemini
provider). The agent is asked to PLOT a clearly-chartable column; `execute_action`
must capture the resulting Plotly figure as JSON into `result["charts"]`.

Driven via `run_agent(..., run_selector=True, skip_clarification=True)` (mirrors
`test_preflight_real.py`'s dataset fixture + uploads_dir monkeypatch) against the
production SQLite driver (the isolated copy via `_isolated_db`). Asserts CONTENT:
at least one chart captured, and the first chart is valid Plotly figure JSON
carrying the `data` + `layout` keys.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from db.models import DatasetRow
from db.session import create_db_session
from graph import nodes as nodes_module
from graph.runner import run_agent


@pytest.fixture(autouse=True)
def uploads_dir(tmp_path, monkeypatch):
    """Point BOTH the nodes' and the runner's uploads dir at a tmp dir."""
    import graph.runner as runner_module

    d = tmp_path / "uploads"
    d.mkdir()
    monkeypatch.setattr(nodes_module, "_uploads_dir", lambda: d)
    monkeypatch.setattr(runner_module, "_uploads_dir", lambda: d)
    return d


@pytest.fixture(autouse=True)
def _clear_session_cache():
    nodes_module._session_cache.clear()
    yield
    nodes_module._session_cache.clear()


def _make_dataset(uploads_dir, filename: str, df: pd.DataFrame) -> str:
    with create_db_session() as session:
        row = DatasetRow(
            filename=filename,
            file_path="",
            row_count=len(df),
            col_count=len(df.columns),
            columns_json=[{"name": str(c), "dtype": str(df[c].dtype)} for c in df.columns],
            content_hash=f"hash-{filename}",
            format="csv",
            origin="uploaded",
        )
        session.add(row)
        session.flush()
        dataset_id = row.id
        csv_path = uploads_dir / f"{dataset_id}.csv"
        df.to_csv(csv_path, index=False)
        df.to_parquet(uploads_dir / f"{dataset_id}.parquet")
        row.file_path = str(csv_path)
    return dataset_id


@pytest.mark.usefixtures("_require_llm_key")
def test_real_gemini_captures_a_plotly_chart(uploads_dir):
    """Ask the real model to plot a histogram of a chartable column -> a Plotly
    figure JSON is captured in result["charts"]."""
    rng = np.random.default_rng(42)
    df = pd.DataFrame({"value": rng.normal(loc=50, scale=12, size=300).round(2)})
    dataset_id = _make_dataset(uploads_dir, "measurements.csv", df)

    # An explicit, unambiguous plotting instruction so gemini-3.1-flash-lite
    # reliably emits a Plotly express figure expression.
    question = (
        "Plot a histogram of the `value` column as a Plotly figure using "
        "plotly express, e.g. px.histogram(df, x='value'). Return the figure "
        "object so it is captured, then give your FINAL ANSWER describing the "
        "distribution."
    )
    result = run_agent(
        question,
        [dataset_id],
        run_selector=True,
        skip_clarification=True,
    )

    assert result["type"] == "answer", f"expected an answer, got {result.get('type')}"
    charts = result["charts"]
    assert isinstance(charts, list)
    assert len(charts) >= 1, (
        f"expected at least one captured Plotly chart; got {len(charts)}. "
        f"steps={[s.get('action') for s in result.get('action_history', [])]}"
    )

    # The first chart is valid Plotly figure JSON with the canonical top-level keys.
    fig = json.loads(charts[0])
    assert isinstance(fig, dict)
    assert "data" in fig and "layout" in fig, (
        f"chart JSON missing data/layout keys; got keys {list(fig.keys())}"
    )
    print(f"\n[charts] captured {len(charts)} chart(s); chart[0] top-level keys: {sorted(fig.keys())}")
    print(f"[charts] data trace count: {len(fig['data'])}")
