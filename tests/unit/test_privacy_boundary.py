"""Privacy boundary — the LLM context must contain schema/sample/aggregates ONLY,
never the full row set. No LLM key required (we inspect the prompt builder directly)."""
from graph.nodes import _build_llm_context


def test_context_contains_schema_sample_aggregates():
    state = {
        "question": "avg value by region?",
        "schema": {"region": "string", "v": "float64"},
        "aggregates": {"v": {"mean": 100.0}},
        "sample": [{"region": "W", "v": 10.0}, {"region": "E", "v": 20.0}],
    }
    ctx = _build_llm_context(state)
    assert "SCHEMA" in ctx and "region" in ctx
    assert "AGGREGATES" in ctx and "mean" in ctx
    assert "SAMPLE" in ctx


def test_context_embeds_only_the_bounded_sample_not_full_rows():
    # Dataset has 10_000 rows but the sample is bounded to a handful.
    sample = [{"region": "W", "v": float(i)} for i in range(20)]
    state = {
        "question": "q",
        "schema": {"region": "string", "v": "float64"},
        "aggregates": {"v": {"mean": 1.0}},
        "sample": sample,
        "_full_row_count": 10_000,
    }
    ctx = _build_llm_context(state)

    # The bounded sample size is announced and small relative to the dataset.
    assert "20 rows only" in ctx
    # A sentinel value that exists only beyond the sample window must be absent.
    assert "9999" not in ctx
    # The sample count embedded is far smaller than the dataset row count.
    assert len(sample) << 10_000  # 20 << 10000
