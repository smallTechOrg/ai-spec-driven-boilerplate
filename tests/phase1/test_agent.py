"""Phase-1 backend-agent slice tests.

These exercise the LangGraph capability slot (load_profile → build_prompt →
answer → finalize, with the handle_error sink) and the ``run_agent`` runner.

- The end-to-end grounded-answer test hits the REAL Gemini API (key from .env).
  It skips ONLY if no Gemini key is present — never stubs as the default.
- The boundary test needs no LLM: it asserts the prompt built by ``build_prompt``
  contains no raw data row / DataFrame repr — only derived profile fields. This is
  the privacy dealbreaker proof.
- The graceful-failure test proves an unknown dataset yields a ``failed`` RunRow
  with human-readable copy and no exception escaping the runner.
"""

import io

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from datasets.store import save_dataset
from datasets.profiler import build_profile
from db import session as session_module
from db.models import RunRow


# --------------------------------------------------------------------------- #
# Fixture: a frame where the FULL-DATA groupby-sum disagrees with a naive
# per-row / sampled view, so a passing answer proves real whole-file computation.
# --------------------------------------------------------------------------- #
_REGIONS = ["North", "South", "East", "West", "Central"]


def _make_skewed_sales_df() -> pd.DataFrame:
    """≥200 rows, ≥5 regions, engineered so the highest *total* revenue region
    is NOT the region with the highest individual rows.

    "South" gets the single largest per-row values (so any per-row / top-of-file
    sample would name South), but it appears rarely. "North" has modest per-row
    values yet appears far more often, so its TOTAL dominates. Only a full-data
    groupby-sum gets the right answer.
    """
    rows: list[dict] = []

    # North: 150 rows of modest revenue → large total.
    for i in range(150):
        rows.append({"region": "North", "revenue": 100.0 + (i % 5), "units": (i % 4) + 1})

    # South: 10 rows of very large revenue → small total despite biggest rows.
    for i in range(10):
        rows.append({"region": "South", "revenue": 900.0 + (i % 5), "units": (i % 4) + 1})

    # The remaining regions: small filler so there are >= 5 categories.
    filler = ["East", "West", "Central"]
    for i in range(60):
        region = filler[i % len(filler)]
        rows.append({"region": region, "revenue": 120.0 + (i % 7), "units": (i % 4) + 1})

    return pd.DataFrame(rows)


@pytest.fixture
def skewed_sales_id() -> str:
    """Save the skewed sales frame via the store and return its dataset_id."""
    df = _make_skewed_sales_df()
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    row = save_dataset(buf.getvalue().encode("utf-8"), "skewed_sales.csv")
    return row.id


@pytest.fixture
def skewed_sales_df() -> pd.DataFrame:
    return _make_skewed_sales_df()


def _require_gemini() -> None:
    from config.settings import get_settings

    if not get_settings().gemini_api_key:
        pytest.skip("No Gemini key set in .env (AGENT_GEMINI_API_KEY)")


# --------------------------------------------------------------------------- #
# 1. End-to-end grounded answer against REAL Gemini.
# --------------------------------------------------------------------------- #
def test_run_agent_names_highest_total_revenue_region(skewed_sales_id, skewed_sales_df):
    _require_gemini()
    from graph.runner import run_agent

    # The correct answer can ONLY come from a full-data groupby-sum.
    totals = skewed_sales_df.groupby("region")["revenue"].sum()
    expected_region = str(totals.idxmax())
    # Sanity: the per-row-max region differs from the full-total-max region,
    # so the fixture genuinely forces whole-file computation.
    naive_region = str(skewed_sales_df.loc[skewed_sales_df["revenue"].idxmax(), "region"])
    assert expected_region != naive_region

    run_id = run_agent(skewed_sales_id, "Which region has the highest total revenue?")
    assert run_id

    with Session(session_module._engine) as s:
        run = s.get(RunRow, run_id)

    assert run is not None
    assert run.status == "completed", f"run failed: {run.error_message}"
    assert run.error_message is None
    assert run.output_text and run.output_text.strip()
    assert run.dataset_id == skewed_sales_id
    assert run.input_text == "Which region has the highest total revenue?"

    # The grounded answer must NAME the full-data winner (case-insensitive).
    assert expected_region.lower() in run.output_text.lower(), (
        f"expected {expected_region!r} in answer, got: {run.output_text!r}"
    )


# --------------------------------------------------------------------------- #
# 2. Boundary assertion — build_prompt leaks no raw rows (no LLM needed).
# --------------------------------------------------------------------------- #
def test_build_prompt_contains_no_raw_rows(skewed_sales_id, skewed_sales_df):
    from graph.nodes import load_profile, build_prompt

    state = {
        "run_id": "test-run",
        "dataset_id": skewed_sales_id,
        "question": "Which region has the highest total revenue?",
        "error": None,
    }
    state = {**state, **load_profile(state)}
    assert state.get("error") is None
    assert state.get("profile")

    state = {**state, **build_prompt(state)}
    assert state.get("error") is None
    prompt = state["prompt"]
    assert isinstance(prompt, str) and prompt

    # The question must be present (it crosses the boundary by design).
    assert "highest total revenue" in prompt.lower()

    # No full raw data row may appear verbatim in the prompt.
    for i in range(len(skewed_sales_df)):
        full_row = ",".join(str(v) for v in skewed_sales_df.iloc[i].tolist())
        assert full_row not in prompt, f"raw row {i} leaked into prompt"

    # No full column may leak either.
    full_revenue_col = ",".join(str(v) for v in skewed_sales_df["revenue"].tolist())
    assert full_revenue_col not in prompt

    # The raw DataFrame repr must be absent.
    assert skewed_sales_df.to_string() not in prompt
    assert "DataFrame" not in prompt


# --------------------------------------------------------------------------- #
# 3. Graceful failure — unknown dataset, no exception escapes the runner.
# --------------------------------------------------------------------------- #
def test_run_agent_unknown_dataset_fails_gracefully():
    from graph.runner import run_agent

    run_id = run_agent("nonexistent-id", "anything at all?")
    assert run_id

    with Session(session_module._engine) as s:
        run = s.get(RunRow, run_id)

    assert run is not None
    assert run.status == "failed"
    assert run.output_text is None
    assert run.error_message and isinstance(run.error_message, str)
    assert "Traceback" not in run.error_message


# --------------------------------------------------------------------------- #
# 4. Edge: an average question stays grounded in the profile (REAL Gemini).
# --------------------------------------------------------------------------- #
def test_run_agent_answers_average_question(skewed_sales_id, skewed_sales_df):
    _require_gemini()
    from graph.runner import run_agent

    mean_units = float(skewed_sales_df["units"].mean())

    run_id = run_agent(skewed_sales_id, "What is the average number of units?")
    with Session(session_module._engine) as s:
        run = s.get(RunRow, run_id)

    assert run.status == "completed", f"run failed: {run.error_message}"
    assert run.output_text and run.output_text.strip()
    # The mean is small (~2.5); assert the rounded integer or one-decimal form
    # appears, proving grounding in the real profile statistic.
    candidates = {
        str(round(mean_units)),
        f"{mean_units:.1f}",
        f"{mean_units:.2f}",
    }
    assert any(c in run.output_text for c in candidates), (
        f"expected one of {candidates} in answer, got: {run.output_text!r}"
    )
