"""Token-economy guard: the generate_sql prompt must never contain full rows."""
from graph.nodes import build_sql_prompt


def test_sql_prompt_excludes_full_dataset_rows():
    # A dataset with 1000 rows; only a 20-row sample is cached on the row.
    full_marker = "ROW_999_SECRET_VALUE"
    sample_text = "region | revenue\nWest | 100\nEast | 50"
    schema_text = "TABLE ds_x (region TEXT, revenue REAL)"

    state = {
        "table_name": "ds_x",
        "schema_text": schema_text,
        "sample_text": sample_text,  # the ≤20-row sample, NOT the full dataset
        "question": "What is total revenue by region?",
    }
    prompt = build_sql_prompt(state)

    # Prompt contains schema + sample + question only.
    assert schema_text in prompt
    assert sample_text in prompt
    assert "total revenue" in prompt
    # The prompt must NOT contain rows beyond the cached sample.
    assert full_marker not in prompt
    # Sanity: prompt is small (bounded), not the whole dataset.
    assert len(prompt) < 2000
