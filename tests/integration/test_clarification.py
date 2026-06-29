"""Integration tests for the clarification flow (real LLM via .env)."""
import pytest
import os
import csv
import tempfile
from pathlib import Path


@pytest.fixture
def ambiguous_csv(tmp_path):
    """CSV with ambiguous numeric columns: val1, val2."""
    p = tmp_path / "ambiguous.csv"
    with open(p, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "val1", "val2"])
        for i in range(10):
            writer.writerow([i, i * 2.5, i * 3.1])
    return str(p)


@pytest.fixture
def clear_csv(tmp_path):
    """CSV with a single clear numeric column: revenue."""
    p = tmp_path / "sales.csv"
    with open(p, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["month", "revenue"])
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        for i, m in enumerate(months):
            writer.writerow([m, (i + 1) * 1000])
    return str(p)


def _make_uploaded_files(csv_path: str, filename: str):
    """Build minimal uploaded_files list with profile."""
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
                "min": float(desc["min"]),
                "max": float(desc["max"]),
                "mean": float(desc["mean"]),
                "std": float(desc["std"]),
                "p25": float(desc["25%"]),
                "p50": float(desc["50%"]),
                "p75": float(desc["75%"]),
            }
        else:
            vc = df[col].value_counts().head(5)
            col_info["value_counts"] = {str(k): int(v) for k, v in vc.items()}
        columns.append(col_info)

    profile = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns,
        "quality_flags": [],
    }
    return [{
        "file_id": "test-file-1",
        "filename": filename,
        "path": csv_path,
        "profile_json": profile,
    }]


def test_ambiguous_question_triggers_clarification(ambiguous_csv, tmp_path):
    """Ambiguous question on multi-numeric CSV should trigger a clarification response."""
    # Build state manually and invoke the node directly
    from graph.nodes import needs_clarification
    from graph.state import AgentState

    uploaded = _make_uploaded_files(ambiguous_csv, "ambiguous.csv")
    state: AgentState = {
        "session_id": "test-clarify-session",
        "action": "answer",
        "current_question": "Show me the trend",
        "uploaded_files": uploaded,
    }

    result = needs_clarification(state)

    # Should have set action=clarification and answer to a clarification question
    assert result.get("action") == "clarification", (
        f"Expected action='clarification' but got action='{result.get('action')}', "
        f"answer='{result.get('answer')}'"
    )
    assert result.get("answer"), "Clarification answer should be non-empty"
    # The clarification question should reference the ambiguous columns
    answer_lower = result["answer"].lower()
    assert any(col in answer_lower for col in ["val1", "val2", "column", "which"]), (
        f"Clarification should reference ambiguous columns or ask 'which'. Got: {result['answer']}"
    )


def test_clear_question_proceeds_without_clarification(clear_csv):
    """Clear, unambiguous question should return PROCEED (no clarification)."""
    from graph.nodes import needs_clarification
    from graph.state import AgentState

    uploaded = _make_uploaded_files(clear_csv, "sales.csv")
    state: AgentState = {
        "session_id": "test-clear-session",
        "action": "answer",
        "current_question": "What is the total revenue?",
        "uploaded_files": uploaded,
    }

    result = needs_clarification(state)

    # Should NOT have set action=clarification
    assert result.get("action") != "clarification", (
        f"Clear question should not trigger clarification but got action='{result.get('action')}'"
    )
    # answer should not be set by this node
    assert not result.get("answer"), (
        f"Clear question should not set answer in needs_clarification, but got: {result.get('answer')}"
    )


def test_full_pipeline_clarification_via_runner(ambiguous_csv, tmp_path):
    """End-to-end: runner returns action=clarification for ambiguous question."""
    from graph.runner import run_question

    uploaded = _make_uploaded_files(ambiguous_csv, "ambiguous.csv")
    result = run_question(
        session_id="test-runner-clarify",
        question="Show me the trend",
        uploaded_files=uploaded,
    )

    assert "action" in result, "run_question must return 'action' key"
    assert result["action"] == "clarification", (
        f"Expected action=clarification from runner but got '{result['action']}'. Answer: {result.get('answer')}"
    )
    assert result.get("answer"), "Clarification answer must be non-empty"
