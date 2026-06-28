"""
Phase 1 integration tests for the Data Analysis Agent.

These tests call the real Gemini API and require AGENT_GEMINI_API_KEY in .env.
The DB is isolated via the autouse _isolated_db fixture in conftest.py (SQLite).
"""

from __future__ import annotations

import json
import os

import pandas as pd
import pytest

def _has_gemini_key() -> bool:
    """Check for AGENT_GEMINI_API_KEY in env or .env file."""
    if os.getenv("AGENT_GEMINI_API_KEY"):
        return True
    # Load .env manually to check
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("AGENT_GEMINI_API_KEY=") and "=" in line:
                    val = line.split("=", 1)[1].strip()
                    return bool(val)
    except FileNotFoundError:
        pass
    return False


# Skip entire module if AGENT_GEMINI_API_KEY not set
pytestmark = pytest.mark.skipif(
    not _has_gemini_key(),
    reason="AGENT_GEMINI_API_KEY not set — skipping Phase 1 agent integration tests",
)


@pytest.fixture
def sales_csv(tmp_path) -> str:
    """Create a real CSV with varied sales data for meaningful analysis."""
    data = {
        "region": ["North", "South", "East", "West", "Central"] * 20,
        "month": list(range(1, 13)) * 8 + [1, 2, 3, 4],
        "revenue": [12500, 9800, 15200, 8700, 6300] * 20,
        "units": [42, 31, 58, 29, 21] * 20,
    }
    df = pd.DataFrame(data)
    csv_path = tmp_path / "sales.csv"
    df.to_csv(csv_path, index=False)
    return str(csv_path)


@pytest.fixture
def uploaded_file_id(sales_csv, _isolated_db) -> str:
    """Insert an UploadedFile record into the isolated test DB and return file_id."""
    from sqlalchemy.orm import sessionmaker
    from db.models import UploadedFile

    df = pd.read_csv(sales_csv)
    schema_info = {
        "columns": list(df.columns),
        "dtypes": df.dtypes.apply(str).to_dict(),
        "sample_rows": df.head(3).where(pd.notnull(df.head(3)), None).values.tolist(),
    }

    file_id = "test-sales-file-001"
    with sessionmaker(bind=_isolated_db)() as session:
        file_row = UploadedFile(
            id=file_id,
            original_name="sales.csv",
            file_path=sales_csv,
            source_type="csv",
            row_count=len(df),
            file_size_bytes=os.path.getsize(sales_csv),
            schema_json=json.dumps(schema_info),
        )
        session.add(file_row)
        session.commit()

    return file_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_full_pipeline_total_revenue_by_region(uploaded_file_id, _isolated_db):
    """
    Full end-to-end: load CSV → plan code → execute → reason → finalize.
    Verifies real Gemini API calls produce a structured answer + chart spec.
    """
    from graph.runner import run_agent

    result = run_agent(
        file_id=uploaded_file_id,
        question="What is the total revenue by region?",
    )

    # Status must be completed
    assert result["status"] == "completed", (
        f"Expected status=completed but got: {result.get('status')!r}. "
        f"Error: {result.get('error')}"
    )

    # Must have an answer
    answer = result.get("answer_text") or result.get("answer")
    assert answer and len(answer) > 10, f"Answer too short or missing: {answer!r}"

    # Must have a chart spec (revenue by region is a good bar chart candidate)
    chart = result.get("chart_spec")
    assert chart is not None, "Expected a chart_spec for regional revenue breakdown"
    assert isinstance(chart, dict), f"chart_spec must be a dict, got {type(chart)}"
    assert "data" in chart, "chart_spec must have 'data' key"
    assert "layout" in chart, "chart_spec must have 'layout' key"
    assert isinstance(chart["data"], list), "chart_spec.data must be a list"
    assert len(chart["data"]) >= 1, "chart_spec.data must have at least one trace"
    assert isinstance(chart["layout"], dict), "chart_spec.layout must be a dict"

    # Each trace must have a 'type' key
    for trace in chart["data"]:
        assert "type" in trace, f"Each chart trace must have a 'type' key; got {trace}"


def test_full_pipeline_scalar_result(uploaded_file_id, _isolated_db):
    """
    Scalar result (row count) should produce an answer_text and null chart_spec.
    """
    from graph.runner import run_agent

    result = run_agent(
        file_id=uploaded_file_id,
        question="How many rows are in the dataset?",
    )

    assert result["status"] == "completed", (
        f"Expected status=completed. Error: {result.get('error')}"
    )

    answer = result.get("answer_text") or result.get("answer")
    assert answer and len(answer) > 5, f"Answer missing or too short: {answer!r}"

    # Scalar questions often return null chart_spec — that is valid
    # We don't assert chart_spec is None since the LLM may choose to chart it
    # The key check: status=completed and we have an answer


def test_error_path_missing_file_id(_isolated_db):
    """
    Agent must handle a missing file_id gracefully — return status=failed,
    not raise an exception.
    """
    from graph.runner import run_agent

    result = run_agent(
        file_id="nonexistent-file-id-9999",
        question="What is the total revenue?",
    )

    assert result["status"] == "failed", (
        f"Expected status=failed for missing file, got: {result.get('status')!r}"
    )
    assert result.get("error") is not None, "Expected an error message for missing file"
    # run_id must still be set
    assert result.get("run_id"), "run_id must always be set"


def test_analysis_run_endpoint(uploaded_file_id, api_client):
    """
    HTTP round-trip: POST /api/analysis/run returns 200 with structured data.
    """
    response = api_client.post(
        "/api/analysis/run",
        json={
            "file_id": uploaded_file_id,
            "question": "What is the total revenue by region?",
        },
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )

    body = response.json()
    assert "data" in body, f"Response must have 'data' key: {body}"

    data = body["data"]
    assert data.get("run_id"), "run_id must be in response"
    assert data.get("status") in ("completed", "failed"), (
        f"Status must be completed or failed, got: {data.get('status')!r}"
    )


def test_analysis_run_endpoint_file_not_found(api_client):
    """POST /api/analysis/run returns 404 when file_id is not in DB."""
    response = api_client.post(
        "/api/analysis/run",
        json={
            "file_id": "does-not-exist",
            "question": "What is the revenue?",
        },
    )
    assert response.status_code == 404, (
        f"Expected 404 for missing file_id, got {response.status_code}"
    )


def test_list_runs_endpoint(api_client):
    """GET /api/analysis/runs returns 200 with runs list and total."""
    response = api_client.get("/api/analysis/runs")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    body = response.json()
    data = body.get("data", {})
    assert "runs" in data, "Response data must have 'runs' key"
    assert "total" in data, "Response data must have 'total' key"
    assert isinstance(data["runs"], list), "runs must be a list"


def test_list_runs_invalid_limit(api_client):
    """GET /api/analysis/runs?limit=0 returns 400."""
    response = api_client.get("/api/analysis/runs?limit=0")
    assert response.status_code == 400, (
        f"Expected 400 for invalid limit, got {response.status_code}"
    )


def test_data_locality_raw_rows_not_sent_to_llm(tmp_path, monkeypatch, _isolated_db):
    """
    Verify that the full CSV raw data is NOT sent to the LLM.
    Only the aggregated result_sample (≤500 rows) should appear in the LLM prompt.
    The raw sentinel values from individual rows must not be in the plan_analysis prompt.
    """
    import json
    import pandas as pd
    from unittest.mock import patch, MagicMock
    from sqlalchemy.orm import sessionmaker
    from db.models import UploadedFile, AnalysisRun
    from db import session as session_module

    db_engine = _isolated_db

    # Create a CSV with a distinctive sentinel value in raw rows
    # The sentinel should only appear in the RESULT, not as a raw row in an LLM prompt
    SENTINEL = "RAWROW_SENTINEL_99999"
    data = {
        "product": [SENTINEL, "B", "C", "D"] * 25,  # 100 rows with sentinel in raw data
        "revenue": [99999, 100, 200, 300] * 25,
    }
    df = pd.DataFrame(data)
    csv_path = tmp_path / "sentinel.csv"
    df.to_csv(csv_path, index=False)

    schema_info = {
        "columns": list(df.columns),
        "dtypes": df.dtypes.apply(str).to_dict(),
        "sample_rows": df.head(3).values.tolist()
    }

    with sessionmaker(bind=db_engine)() as sess:
        file_row = UploadedFile(
            id="sentinel-test-001",
            original_name="sentinel.csv",
            file_path=str(csv_path),
            source_type="csv",
            row_count=len(df),
            file_size_bytes=csv_path.stat().st_size,
            schema_json=json.dumps(schema_info),
        )
        sess.add(file_row)
        sess.commit()

    # Capture what is sent to _gemini_call for the reason_answer node
    captured_reason_messages = []

    import graph.nodes as nodes_module
    original_fn = nodes_module._gemini_call

    def spy_gemini_call(model, system_prompt, user_message, **kwargs):
        # Capture the user_message for the reason_answer call (uses gemini-2.5-pro)
        from config.settings import get_settings
        s = get_settings()
        if model == (s.llm_model_reason or "gemini-2.5-pro"):
            captured_reason_messages.append(user_message)
        return original_fn(model, system_prompt, user_message, **kwargs)

    monkeypatch.setattr(nodes_module, "_gemini_call", spy_gemini_call)

    from graph.runner import run_agent
    result = run_agent(file_id="sentinel-test-001", question="What is the total revenue?")

    # The run should succeed (or at least reach reason_answer)
    # Most importantly: the reason_answer LLM call must NOT contain the full raw SENTINEL rows
    # It should only contain the aggregated result (total revenue)
    assert len(captured_reason_messages) > 0, "reason_answer was never called — pipeline did not reach that node"

    reason_msg = captured_reason_messages[0]

    # The result_sample sent to reason_answer should be the aggregated result (a scalar or small df)
    # NOT the full 100-row raw data with SENTINEL appearing 25 times
    sentinel_count = reason_msg.count(SENTINEL)
    # The schema_info sample (first 3 rows) may legitimately include SENTINEL once
    # but the full dataset (25 occurrences) must NOT be there
    assert sentinel_count <= 3, (
        f"Raw data rows sent to LLM! SENTINEL appeared {sentinel_count} times in reason_answer prompt. "
        f"Only aggregated results (≤ first 3 sample rows) should reach the LLM."
    )
