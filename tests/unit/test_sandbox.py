"""Unit tests for the local restricted-namespace pandas sandbox.

Real behaviour, no mocks: a small in-test DataFrame is built with pandas and
LLM-style snippets are executed through ``sandbox.run``.
"""

import time

import pandas as pd
import pytest

from src.tools import sandbox


@pytest.fixture()
def df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region": ["north", "south", "north", "south", "west"],
            "amount": [10.0, 20.0, 30.0, 5.0, 100.0],
        }
    )


def test_valid_sum_snippet_returns_real_sum(df: pd.DataFrame) -> None:
    expected = float(df["amount"].sum())  # hand-computed: 165.0
    out = sandbox.run("result = df['amount'].sum()", df)
    assert out["ok"] is True
    assert out["result"] == expected
    assert out["result"] == 165.0


def test_groupby_idxmax_returns_correct_region(df: pd.DataFrame) -> None:
    # west has the single highest mean (100.0); north=20.0, south=12.5.
    out = sandbox.run(
        "result = df.groupby('region')['amount'].mean().idxmax()", df
    )
    assert out["ok"] is True
    assert out["result"] == "west"


def test_groupby_mean_series_coerced_to_dict(df: pd.DataFrame) -> None:
    out = sandbox.run("result = df.groupby('region')['amount'].mean()", df)
    assert out["ok"] is True
    assert isinstance(out["result"], dict)
    assert out["result"]["west"] == 100.0


def test_erroring_code_returns_structured_error_not_raise(df: pd.DataFrame) -> None:
    out = sandbox.run("result = df['nope'].sum()", df)
    assert out["ok"] is False
    assert out["error"]
    assert "traceback_summary" in out


def test_missing_result_assignment_returns_error(df: pd.DataFrame) -> None:
    out = sandbox.run("answer = df['amount'].sum()", df)
    assert out["ok"] is False
    assert "result" in out["error"].lower()


def test_forbidden_import_is_blocked(df: pd.DataFrame) -> None:
    out = sandbox.run("import os\nresult = os.getcwd()", df)
    assert out["ok"] is False


def test_forbidden_open_is_blocked(df: pd.DataFrame) -> None:
    out = sandbox.run("result = open('/etc/hosts').read()", df)
    assert out["ok"] is False


def test_forbidden_dunder_import_is_blocked(df: pd.DataFrame) -> None:
    out = sandbox.run("result = __import__('os').listdir('.')", df)
    assert out["ok"] is False


def test_timeout_returns_structured_timeout_error(df: pd.DataFrame) -> None:
    started = time.perf_counter()
    out = sandbox.run(
        "x = 0\nwhile True:\n    x += 1\nresult = x",
        df,
        timeout_s=0.2,
    )
    elapsed = time.perf_counter() - started
    assert out["ok"] is False
    assert "timeout" in out["error"].lower()
    assert "traceback_summary" in out
    # We returned promptly after the timeout, not after the loop finished.
    assert elapsed < 5.0


def test_nan_result_coerced_to_none(df: pd.DataFrame) -> None:
    # mean of an empty selection → NaN → None
    out = sandbox.run("result = df[df['amount'] > 1000]['amount'].mean()", df)
    assert out["ok"] is True
    assert out["result"] is None


def test_dataframe_result_coerced_to_records(df: pd.DataFrame) -> None:
    out = sandbox.run("result = df.head(2)", df)
    assert out["ok"] is True
    assert isinstance(out["result"], list)
    assert out["result"][0]["region"] == "north"
