"""Privacy spine: no raw data row value ever reaches a Gemini-bound prompt.

We plant a unique sentinel value in a cell, run the full analysis graph against
real Gemini, capture every outbound prompt (and system prompt) sent to the LLM
client, and assert the sentinel never appears. The build_*_prompt functions are
also asserted directly as the single prompt-assembly point.
"""
import pandas as pd
import pytest

from graph.nodes import build_code_prompt, build_finalize_prompt, build_plan_prompt

SENTINEL = "ZZZSENTINEL_9f3a_DO_NOT_LEAK"


@pytest.fixture
def dataset_with_sentinel(tmp_path):
    """Create + persist a dataset whose first row holds a unique sentinel value."""
    from db.session import create_db_session
    from graph.runner import profile_and_store

    df = pd.DataFrame(
        {
            "customer": [SENTINEL, "Acme", "Globex", "Initech"],
            "revenue": [100, 250, 175, 300],
        }
    )
    path = tmp_path / "secret.csv"
    df.to_csv(path, index=False)

    with create_db_session() as session:
        dataset, _profile = profile_and_store(
            session,
            name="secret.csv",
            kind="csv",
            file_path=str(path),
            size_bytes=path.stat().st_size,
        )
        dataset_id = dataset.id
    return dataset_id


def test_build_prompts_exclude_raw_rows():
    """The prompt builders only ever interpolate question + profile + summaries."""
    profile = {
        "columns": [
            {"name": "customer", "dtype": "object", "non_null": 4, "n_unique": 4}
        ],
        "row_count": 4,
        "column_count": 2,
    }
    question = "How many customers are there?"

    plan_prompt = build_plan_prompt(question, profile)
    code_prompt = build_code_prompt(question, profile, "count rows")
    final_prompt = build_finalize_prompt(question, {"type": "scalar", "value": 4})

    for prompt in (plan_prompt, code_prompt, final_prompt):
        assert question in prompt
        assert SENTINEL not in prompt


@pytest.mark.usefixtures("_require_llm_key")
def test_no_raw_rows_in_outbound_prompts(dataset_with_sentinel, monkeypatch):
    """End-to-end: capture every Gemini-bound prompt; sentinel must never appear."""
    from graph.runner import run_analysis
    from llm.client import LLMClient

    captured: list[str] = []
    real_call = LLMClient.call_with_usage

    def spy(self, prompt, *, system=None):
        captured.append(prompt)
        if system:
            captured.append(system)
        return real_call(self, prompt, system=system)

    monkeypatch.setattr(LLMClient, "call_with_usage", spy)

    run_id = run_analysis(dataset_with_sentinel, "How many unique customers are there?")
    assert run_id is not None

    # The graph made at least the plan + generate_code + finalize calls.
    assert len(captured) >= 3
    for payload in captured:
        assert SENTINEL not in payload, "raw row value leaked into an LLM prompt"
