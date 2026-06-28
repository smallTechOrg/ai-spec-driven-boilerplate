"""Local executor tests — no LLM key required."""
import pandas as pd
import pytest

from analysis.executor import execute_code, ExecutionError


def _df():
    return pd.DataFrame({"region": ["W", "E", "W"], "v": [10.0, 20.0, 30.0]})


def test_executes_over_full_dataframe():
    out = execute_code(
        "result = df.groupby('region')['v'].mean().to_dict()", _df()
    )
    assert out["result"] == {"W": 20.0, "E": 20.0}


def test_missing_result_raises_recoverable_error():
    with pytest.raises(ExecutionError):
        execute_code("x = 1", _df())


def test_runtime_error_is_wrapped():
    with pytest.raises(ExecutionError):
        execute_code("result = df['nope'].mean()", _df())


def test_restricted_namespace_blocks_open():
    with pytest.raises(ExecutionError):
        execute_code("result = open('/etc/passwd').read()", _df())


def test_restricted_namespace_blocks_import():
    with pytest.raises(ExecutionError):
        execute_code("import os\nresult = os.listdir('.')", _df())


def test_chart_spec_passes_through():
    code = (
        "result = df.groupby('region')['v'].mean().to_dict()\n"
        "chart_spec = {'mark': 'bar', 'encoding': {'x': {'field': 'region'}}}"
    )
    out = execute_code(code, _df())
    assert out["chart_spec"]["mark"] == "bar"
