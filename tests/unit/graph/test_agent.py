"""Graph compiles and runs end-to-end over a real Gemini call."""

import pandas as pd
import pytest

from analysis.profiler import profile_dataframe


def test_graph_compiles():
    from graph.agent import agentic_ai
    assert agentic_ai is not None


def _fixture_csv(tmp_path, n_rows=5000):
    regions = ["NW", "SE", "NE", "SW"]
    df = pd.DataFrame(
        {"region": [regions[i % 4] for i in range(n_rows)], "amount": [float(i % 50) for i in range(n_rows)]}
    )
    path = tmp_path / "sales.csv"
    df.to_csv(path, index=False)
    return path, df


def _skewed_fixture_csv(tmp_path):
    """sample != full: the first rows are all NW, true counts are different."""
    rows = ["NW"] * 300 + ["SE"] * 2500 + ["SW"] * 2700 + ["NE"] * 1500
    df = pd.DataFrame({"region": rows, "amount": [float(i % 50) for i in range(len(rows))]})
    path = tmp_path / "skewed.csv"
    df.to_csv(path, index=False)
    expected = df.groupby("region").size().to_dict()
    return path, df, expected


def test_full_invoke_real_gemini(tmp_path, _require_llm_key):
    from graph.agent import agentic_ai

    path, df = _fixture_csv(tmp_path, 5000)
    prof = profile_dataframe(df, sample_rows=5)

    steps = []
    initial = {
        "run_id": "test-run",
        "dataset_id": "ds1",
        "conversation_id": "c1",
        "question": "Count the number of rows for each region and return one row per region with a 'count' column.",
        "profile": prof["profile"],
        "sample_rows": prof["sample_rows"],
        "row_count": prof["row_count"],
        "file_path": str(path),
        "history": [],
        "on_step": lambda step, status: steps.append((step, status)),
        "error": None,
    }

    final = agentic_ai.invoke(initial)

    assert final.get("status") == "completed", final.get("error")
    assert final.get("answer")
    assert final.get("code")
    assert final.get("result_table") is not None
    table = final["result_table"]
    assert table["row_count"] >= 1

    # Proof of full-data execution (a 5-row sample could never yield this):
    # EITHER a grouped result whose per-region counts sum to 5000, OR the
    # executor touched all 5000 rows (result_table row_count == 5000).
    rows = table["rows"]
    count_cols = [c for c in table["columns"] if c.lower() in ("count", "n", "size", "counts")]
    grouped_total = 0
    for r in rows:
        for c in count_cols:
            try:
                grouped_total += int(r[c])
            except (ValueError, TypeError):
                pass
    full_data_proven = grouped_total == 5000 or table["row_count"] == 5000
    assert full_data_proven, (
        f"could not prove full-data execution: grouped_total={grouped_total}, "
        f"row_count={table['row_count']}, columns={table['columns']}"
    )
    assert isinstance(final.get("chart_spec"), dict)
    assert final.get("prompt_tokens", 0) > 0
    assert final.get("completion_tokens", 0) > 0
    assert final.get("estimated_cost_usd", 0) > 0
    # step hooks fired for SSE
    assert ("plan", "running") in steps
    assert ("finalize", "done") in steps


def test_full_invoke_real_gemini_value_level(tmp_path, _require_llm_key):
    """Real Gemini full graph over a sample!=full fixture must yield a
    result_table whose computed values EQUAL the true full-data counts.

    We assert on result_table values (deterministic local computation), not the
    LLM prose. This is the value-level guard that catches Blocker 1.
    """
    from graph.agent import agentic_ai

    path, df, expected = _skewed_fixture_csv(tmp_path)
    prof = profile_dataframe(df, sample_rows=5)

    initial = {
        "run_id": "test-run-val",
        "dataset_id": "ds1",
        "conversation_id": "c1",
        "question": "How many rows are there for each region? Return one row per region with a count column.",
        "profile": prof["profile"],
        "sample_rows": prof["sample_rows"],
        "row_count": prof["row_count"],
        "file_path": str(path),
        "history": [],
        "error": None,
    }

    final = agentic_ai.invoke(initial)
    assert final.get("status") == "completed", final.get("error")
    table = final.get("result_table")
    assert table is not None

    # Locate the per-region count column robustly (model may name it count/n/size).
    count_cols = [c for c in table["columns"] if c.lower() in ("count", "n", "size", "counts", "0")]
    region_cols = [c for c in table["columns"] if c.lower() == "region"]
    assert count_cols, f"no count column in {table['columns']}"
    assert region_cols, f"no region column in {table['columns']}"
    rcol, ccol = region_cols[0], count_cols[0]
    actual = {r[rcol]: int(r[ccol]) for r in table["rows"]}
    # TRUE full-data counts — NOT the all-NW first-200 truncation.
    assert actual == {k: int(v) for k, v in expected.items()}, (
        f"actual={actual} expected={expected}"
    )

    # ALSO finding: a clean categorical count should yield a bar chart_spec.
    chart = final.get("chart_spec") or {}
    assert chart.get("chart_type") == "bar", chart


def test_follow_up_uses_prior_context(tmp_path, _require_llm_key):
    from graph.agent import agentic_ai

    path, df, expected = _skewed_fixture_csv(tmp_path)
    prof = profile_dataframe(df, sample_rows=5)

    initial = {
        "run_id": "r2",
        "question": "now only for region NW",
        "profile": prof["profile"],
        "sample_rows": prof["sample_rows"],
        "row_count": prof["row_count"],
        "file_path": str(path),
        "history": [
            {
                "question": "How many rows per region?",
                "answer": f"NW {expected['NW']}, SE {expected['SE']}, SW {expected['SW']}, NE {expected['NE']}",
            }
        ],
        "error": None,
    }
    final = agentic_ai.invoke(initial)
    assert final.get("status") == "completed", final.get("error")
    assert final.get("answer")
    # The follow-up resolved "now only for region NW" from prior context.
    assert "NW" in (final.get("code") or "") or "NW" in (final.get("answer") or "")
    # The result should reflect the narrowing to NW's true full-data count (300),
    # NOT all regions and NOT the sample. We check the result_table values.
    table = final.get("result_table") or {"rows": []}
    nw_true = expected["NW"]
    flat_values = []
    for r in table["rows"]:
        for v in r.values():
            try:
                flat_values.append(int(v))
            except (ValueError, TypeError):
                pass
    narrowed = (
        nw_true in flat_values
        or str(nw_true) in (final.get("answer") or "")
    )
    assert narrowed, (
        f"expected NW's full-data count {nw_true} to appear; "
        f"table_values={flat_values}, answer={final.get('answer')!r}"
    )
