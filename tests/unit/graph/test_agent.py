"""Graph structure + error routing — no LLM key required."""
from graph.edges import route_on_error
from graph.nodes import aggregate, handle_error, finalize


def test_graph_compiles():
    """Graph compiles without requiring any env vars."""
    from graph.agent import agentic_ai

    assert agentic_ai is not None


def test_route_on_error_routes_to_handle_error_when_error_set():
    assert route_on_error({"error": "boom"}, "plan") == "handle_error"


def test_route_on_error_proceeds_when_no_error():
    assert route_on_error({"error": None}, "plan") == "plan"
    assert route_on_error({}, "narrate") == "narrate"


def test_handle_error_sets_failed_status():
    out = handle_error({"error": "bad sql"})
    assert out["status"] == "failed"
    assert out["checkpoint"] == "handle_error"


def test_finalize_sets_completed_status():
    out = finalize({})
    assert out["status"] == "completed"
    assert out["checkpoint"] == "finalize"


def test_aggregate_summarizes_and_keeps_metadata():
    # Two low-cardinality regions over 250 raw rows -> the gate summarizes them
    # into derived numbers + category labels, never a dump of the raw rows.
    # The dataset profile reports region as a low-cardinality grouping column.
    rows = [{"region": ["W", "E"][i % 2], "n": i} for i in range(250)]
    cols = [{"name": "region", "type": "VARCHAR"}, {"name": "n", "type": "BIGINT"}]
    profile = {
        "row_count": 250,
        "columns": [
            {"name": "region", "type": "VARCHAR", "distinct_count": 2},
            {"name": "n", "type": "BIGINT", "distinct_count": 250},
        ],
    }
    out = aggregate({"query_rows": rows, "query_columns": cols, "profile": profile})
    agg = out["aggregates"]

    assert agg["row_count"] == 250
    assert agg["result_kind"] == "row_level_summary"   # 250 rows != a grouped result
    assert [c["name"] for c in agg["columns"]] == ["region", "n"]

    # numeric column reduced to derived stats (no raw values listed)
    n_summary = agg["column_summaries"]["n"]
    assert n_summary["kind"] == "numeric"
    assert n_summary["count"] == 250
    assert n_summary["min"] == 0 and n_summary["max"] == 249

    # low-cardinality categorical -> labels + counts emitted (a grouping key)
    region_summary = agg["column_summaries"]["region"]
    assert region_summary["kind"] == "categorical"
    assert region_summary["is_label"] is True
    assert region_summary["distinct_count"] == 2

    # the narration table holds derived data only (group labels + counts)
    assert agg["table"]["columns"] == ["region", "count"]


def test_aggregate_never_emits_high_cardinality_raw_cells():
    """SELECT *-style result: unique-per-row PII / free text must NOT cross.

    The dataset profile reports customer + note as high-cardinality (one distinct
    value per row), so the gate must suppress their values even though `amount` is
    a numeric measure present in the same result.
    """
    rows = [
        {"customer": f"PERSON_{i}", "note": f"secret_note_{i}", "amount": i}
        for i in range(200)
    ]
    cols = [
        {"name": "customer", "type": "VARCHAR"},
        {"name": "note", "type": "VARCHAR"},
        {"name": "amount", "type": "BIGINT"},
    ]
    profile = {
        "row_count": 200,
        "columns": [
            {"name": "customer", "type": "VARCHAR", "distinct_count": 200},
            {"name": "note", "type": "VARCHAR", "distinct_count": 200},
            {"name": "amount", "type": "BIGINT", "distinct_count": 200},
        ],
    }
    out = aggregate({"query_rows": rows, "query_columns": cols, "profile": profile})
    agg = out["aggregates"]

    import json
    blob = json.dumps(agg)
    # The unique per-row tokens are high-cardinality -> they can never appear.
    assert "PERSON_" not in blob
    assert "secret_note_" not in blob

    # They are reported as counts only.
    cust = agg["column_summaries"]["customer"]
    assert cust["is_label"] is False
    assert cust["distinct_count"] == 200
    assert "value_counts" not in cust
    # amount is summarized to derived numbers.
    assert agg["column_summaries"]["amount"]["sum"] == sum(range(200))


def test_aggregate_passes_through_small_grouped_result_labels():
    """A genuine GROUP BY result (few rows, a label + a numeric measure) keeps its
    grouping labels so the answer can name them (e.g. the top region)."""
    rows = [{"region": "West", "total": 1633980.38}]
    cols = [{"name": "region", "type": "VARCHAR"}, {"name": "total", "type": "DOUBLE"}]
    profile = {
        "row_count": 600,
        "columns": [
            {"name": "region", "type": "VARCHAR", "distinct_count": 4},
            {"name": "amount", "type": "DOUBLE", "distinct_count": 600},
        ],
    }
    out = aggregate({"query_rows": rows, "query_columns": cols, "profile": profile})
    agg = out["aggregates"]
    assert agg["result_kind"] == "pre_aggregated"
    # the grouping label "West" crosses (it is a low-card grouping key, not PII)
    assert agg["table"] == {"columns": ["region", "total"], "rows": [["West", 1633980.38]]}


def test_aggregate_fallback_suppresses_row_level_slice_without_profile():
    """No profile + a small raw slice of unique cells must NOT leak values.

    With no dataset cardinality available, a row-level slice (each value unique)
    is summarized, not passed through — even at small row counts."""
    rows = [
        {"customer": f"PERSON_{i}", "secret_note": f"note_{i}", "revenue": 100 - i}
        for i in range(20)
    ]
    cols = [
        {"name": "customer", "type": "VARCHAR"},
        {"name": "secret_note", "type": "VARCHAR"},
        {"name": "revenue", "type": "BIGINT"},
    ]
    out = aggregate({"query_rows": rows, "query_columns": cols})  # no profile
    agg = out["aggregates"]

    import json
    blob = json.dumps(agg)
    assert "PERSON_" not in blob
    assert "note_" not in blob
    assert agg["column_summaries"]["customer"]["is_label"] is False
    assert agg["column_summaries"]["secret_note"]["is_label"] is False
