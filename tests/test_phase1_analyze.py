"""End-to-end analysis against REAL Gemini.

A question whose numeric answer is verifiable against pandas computed directly.
Asserts: status completed, prose answer present, non-empty code that ran locally,
tokens > 0, cost_usd > 0, and the agent's number matches the local truth.
"""
import re

import pandas as pd
import pytest


def _contains_number(text: str, value: int) -> bool:
    """True if `text` states `value`, tolerating thousands separators / decimals
    (e.g. 875 matches '875', '875.00', '8,75'... no — only '875' / '875.0')."""
    normalized = re.sub(r"(?<=\d),(?=\d)", "", text)  # drop thousands commas
    return bool(re.search(rf"(?<!\d){value}(?:\.0+)?(?!\d)", normalized))


@pytest.fixture
def sales_dataset(tmp_path):
    from db.session import create_db_session
    from graph.runner import profile_and_store

    df = pd.DataFrame(
        {
            "region": ["North", "South", "North", "East", "South"],
            "revenue": [100, 250, 175, 300, 50],
        }
    )
    path = tmp_path / "sales.csv"
    df.to_csv(path, index=False)
    truth_total = int(df["revenue"].sum())  # 875

    with create_db_session() as session:
        dataset, _ = profile_and_store(
            session,
            name="sales.csv",
            kind="csv",
            file_path=str(path),
            size_bytes=path.stat().st_size,
        )
        dataset_id = dataset.id
    return dataset_id, truth_total


@pytest.mark.usefixtures("_require_llm_key")
def test_analyze_end_to_end(sales_dataset):
    from db.models import AnalysisRun
    from db.session import create_db_session
    from graph.runner import run_analysis

    dataset_id, truth_total = sales_dataset
    run_id = run_analysis(dataset_id, "What is the total revenue across all rows?")

    with create_db_session() as session:
        run = session.get(AnalysisRun, run_id)
        assert run is not None
        assert run.status == "completed", run.error_message
        assert run.answer and len(run.answer) > 5
        assert run.code and "result" in run.code  # the code that ran locally
        assert run.total_tokens > 0
        assert run.prompt_tokens > 0
        assert run.cost_usd > 0
        # the computed number is real, not hallucinated
        assert _contains_number(run.answer, truth_total), run.answer
        # result summary captured the computed scalar
        assert run.result_summary is not None
