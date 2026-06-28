"""Sandboxed executor — no LLM key required. Captures errors, bounds results,
and (the real boundary) statically AST-guards generated code so it cannot escape
the sandbox or touch the filesystem/network/process."""
import os
import subprocess
from unittest import mock

import pandas as pd

from analysis.executor import (
    check_code_is_safe,
    execute_code,
    extract_code,
    summarize_result,
)


def _df():
    return pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]})


def test_executes_scalar_result():
    out = execute_code("result = df['b'].sum()", _df())
    assert out.error is None
    assert out.summary == {"type": "scalar", "value": 60}


def test_missing_result_is_captured_error():
    out = execute_code("x = 1", _df())
    assert out.summary is None
    assert "result" in out.error


def test_code_exception_is_captured_not_raised():
    out = execute_code("result = df['nope'].sum()", _df())
    assert out.summary is None
    assert out.error is not None  # KeyError captured as a string


def test_open_is_blocked():
    out = execute_code("result = open('/etc/passwd').read()", _df())
    assert out.summary is None
    assert out.error is not None
    assert "blocked" in out.error  # rejected by the AST guard, not run


def test_import_is_blocked():
    out = execute_code("import os\nresult = os.listdir('.')", _df())
    assert out.summary is None
    assert out.error is not None
    assert "blocked" in out.error
    assert "import" in out.error


# --- Sandbox-escape guarantees: the AST guard must REJECT these before exec. ---


def test_subclasses_escape_payload_is_blocked_and_runs_nothing():
    """The classic builtins-sandbox escape: walk the type hierarchy to reach
    subprocess.Popen / os._wrap_close. The AST guard must reject it unrun, and
    crucially NO subprocess may be spawned."""
    payload = (
        "result = ().__class__.__bases__[0].__subclasses__()"
    )
    with mock.patch.object(subprocess, "Popen") as popen, mock.patch.object(
        os, "system"
    ) as system:
        out = execute_code(payload, _df())
    assert out.summary is None
    assert out.error is not None
    assert "blocked" in out.error  # rejected, never executed
    popen.assert_not_called()  # no escape occurred
    system.assert_not_called()


def test_full_popen_escape_chain_is_blocked():
    """Even the fully chained shell-exec payload is rejected statically."""
    payload = (
        "x = [c for c in ().__class__.__bases__[0].__subclasses__() "
        "if c.__name__ == 'Popen'][0]\n"
        "result = x(['echo', 'pwned'])"
    )
    with mock.patch.object(subprocess, "Popen") as popen:
        out = execute_code(payload, _df())
    assert out.summary is None
    assert out.error is not None
    assert "blocked" in out.error
    popen.assert_not_called()


def test_dunder_attribute_access_is_blocked():
    out = execute_code("result = df.__class__", _df())
    assert out.summary is None
    assert out.error is not None
    assert "blocked" in out.error


def test_eval_call_is_blocked():
    out = execute_code("result = eval('1 + 1')", _df())
    assert out.summary is None
    assert out.error is not None
    assert "blocked" in out.error


def test_getattr_introspection_is_blocked():
    out = execute_code("result = getattr(df, 'values')", _df())
    assert out.summary is None
    assert out.error is not None
    assert "blocked" in out.error


def test_legitimate_pandas_snippet_passes_guard_and_runs():
    """A well-behaved groupby snippet must NOT trip the guard and must return
    the correct computed result."""
    df = pd.DataFrame(
        {"region": ["n", "s", "n", "s"], "revenue": [10, 1, 5, 4]}
    )
    code = "result = df.groupby('region')['revenue'].sum().to_dict()"
    assert check_code_is_safe(code) is None
    out = execute_code(code, df)
    assert out.error is None
    assert out.summary["type"] == "scalar"
    assert out.summary["value"] == {"n": 15, "s": 5}


def test_dataframe_result_is_bounded():
    big = pd.DataFrame({"x": range(1000)})
    out = execute_code("result = df", big)
    assert out.error is None
    assert out.summary["type"] == "dataframe"
    assert out.summary["shape"] == [1000, 1]
    assert len(out.summary["rows"]) <= 50
    assert out.summary["truncated"] is True


def test_extract_code_from_fence():
    text = "Here:\n```python\nresult = 1\n```\nDone."
    assert extract_code(text) == "result = 1"


def test_summarize_series():
    s = pd.Series([1, 2, 3], name="vals")
    summary = summarize_result(s)
    assert summary["type"] == "series"
    assert summary["length"] == 3
