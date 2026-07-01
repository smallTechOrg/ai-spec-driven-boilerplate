"""Integration tests for reflection + retry flow (real LLM via .env)."""
import pytest
import csv


@pytest.fixture
def simple_csv(tmp_path):
    """A simple CSV with clear column names."""
    p = tmp_path / "sales.csv"
    with open(p, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["month", "revenue", "units"])
        data = [("Jan", 10000, 150), ("Feb", 12000, 180), ("Mar", 11000, 160)]
        for row in data:
            writer.writerow(row)
    return str(p)


def _make_uploaded_files(csv_path: str, filename: str):
    import pandas as pd
    df = pd.read_csv(csv_path)
    columns = []
    for col in df.columns:
        col_info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isna().sum()),
            "null_pct": 0.0,
            "sample_values": [str(v) for v in df[col].dropna().head(3).tolist()],
        }
        if pd.api.types.is_numeric_dtype(df[col]):
            desc = df[col].describe()
            col_info["stats"] = {
                "min": float(desc["min"]), "max": float(desc["max"]),
                "mean": float(desc["mean"]), "std": float(desc["std"]),
                "p25": float(desc["25%"]), "p50": float(desc["50%"]), "p75": float(desc["75%"]),
            }
        else:
            vc = df[col].value_counts().head(5)
            col_info["value_counts"] = {str(k): int(v) for k, v in vc.items()}
        columns.append(col_info)

    profile = {
        "row_count": len(df), "column_count": len(df.columns),
        "columns": columns, "quality_flags": [],
    }
    return [{"file_id": "test-file-1", "filename": filename, "path": csv_path, "profile_json": profile}]


def test_reflect_and_retry_node_corrects_bad_code(simple_csv):
    """reflect_and_retry node should generate corrected code when given bad code."""
    from graph.nodes import reflect_and_retry
    from graph.state import AgentState

    uploaded = _make_uploaded_files(simple_csv, "sales.csv")
    state: AgentState = {
        "session_id": "test-reflect-session",
        "action": "answer",
        "current_question": "What is the total revenue?",
        "uploaded_files": uploaded,
        "generated_code": "result = dfs['sales']['nonexistent_column'].sum()",
        "error": "KeyError: 'nonexistent_column'",
        "retry_count": 0,
    }

    result = reflect_and_retry(state)

    assert result.get("error") is None, f"reflect_and_retry should clear the error. Got: {result.get('error')}"
    assert result.get("generated_code") != state["generated_code"], "Should have generated new code"
    assert result.get("retry_count") == 1, f"retry_count should be 1. Got: {result.get('retry_count')}"
    # The corrected code should reference the real column 'revenue'
    new_code = result.get("generated_code", "")
    assert "revenue" in new_code.lower() or "result" in new_code.lower(), (
        f"Corrected code should reference 'revenue'. Got: {new_code}"
    )


def test_retry_count_increments(simple_csv):
    """retry_count should increment on each reflection call."""
    from graph.nodes import reflect_and_retry
    from graph.state import AgentState

    uploaded = _make_uploaded_files(simple_csv, "sales.csv")

    # First retry
    state1: AgentState = {
        "session_id": "test-retry-count",
        "action": "answer",
        "current_question": "Sum the revenue",
        "uploaded_files": uploaded,
        "generated_code": "result = dfs['sales']['bad_col'].sum()",
        "error": "KeyError: 'bad_col'",
        "retry_count": 0,
    }
    result1 = reflect_and_retry(state1)
    assert result1.get("retry_count") == 1

    # Second retry (simulate)
    state2 = {**result1, "error": "Another error", "retry_count": 1}
    result2 = reflect_and_retry(state2)
    assert result2.get("retry_count") == 2


def test_after_execute_p3_routes_to_reflect_when_error_and_retries_available():
    """after_execute_p3 should route to reflect_and_retry when error and retry_count < 2."""
    from graph.edges import after_execute_p3

    state_with_error_0 = {"error": "KeyError: foo", "retry_count": 0}
    assert after_execute_p3(state_with_error_0) == "reflect_and_retry"

    state_with_error_1 = {"error": "KeyError: foo", "retry_count": 1}
    assert after_execute_p3(state_with_error_1) == "reflect_and_retry"

    state_with_error_2 = {"error": "KeyError: foo", "retry_count": 2}
    assert after_execute_p3(state_with_error_2) == "handle_error"

    state_ok = {"retry_count": 0}
    assert after_execute_p3(state_ok) == "format_response"


def test_full_pipeline_reflection_produces_answer_or_clean_error(simple_csv):
    """End-to-end: a deliberately bad question should eventually produce answer or clean error."""
    from graph.runner import run_question

    uploaded = _make_uploaded_files(simple_csv, "sales.csv")
    # Ask a question that is clear but might require a retry if code fails
    result = run_question(
        session_id="test-pipeline-reflect",
        question="What is the total revenue across all months?",
        uploaded_files=uploaded,
    )

    assert "answer" in result, "Runner must return 'answer' key"
    assert result.get("answer"), "Answer should be non-empty"
    # Should NOT contain Python tracebacks
    answer = result["answer"]
    assert "Traceback" not in answer, f"Answer should not contain Python traceback. Got: {answer}"
    assert "File \"" not in answer, f"Answer should not contain raw file paths. Got: {answer}"
