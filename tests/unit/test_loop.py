"""Agentic-loop behaviour (recovery + cap) driven through the real graph with a
controllable fake LLM at the provider boundary — deterministic, no key required.

The fake is node-aware via the system prompt so plan/generate_code/finalize are
distinguishable (per harness stub guidance)."""
import pandas as pd
import pytest

import graph.nodes as nodes
from graph.agent import agentic_ai


class _ScriptedLLM:
    """Returns scripted code for generate_code; trivial text otherwise.

    `code_sequence` is consumed one entry per generate_code call so we can force
    an erroring first attempt followed by a good one.
    """

    def __init__(self, code_sequence):
        self._codes = list(code_sequence)

    def call_model(self, prompt, *, system=None):
        s = (system or "").lower()
        if "output only the python code" in s:        # generate_code prompt
            return self._codes.pop(0) if self._codes else "result = None"
        if "respond with the plan text only" in s:    # plan prompt
            return "compute the answer"
        return "Here is the answer."                  # finalize prompt


@pytest.fixture
def _csv(tmp_path):
    p = tmp_path / "d.csv"
    pd.DataFrame({"region": ["W", "E"], "v": [10.0, 30.0]}).to_csv(p, index=False)
    return str(p)


def _state(csv_path, max_steps=4):
    return {
        "run_id": "r1",
        "dataset_id": "d1",
        "storage_path": csv_path,
        "question": "mean v?",
        "schema": {"region": "string", "v": "float64"},
        "sample": [{"region": "W", "v": 10.0}],
        "aggregates": {"v": {"mean": 20.0}},
        "step": 0,
        "max_steps": max_steps,
        "status": "running",
        "error": None,
        "last_error": None,
    }


def test_recovers_from_bad_first_attempt(monkeypatch, _csv):
    # First code errors (bad column), second succeeds.
    scripted = _ScriptedLLM(
        ["result = df['nope'].mean()", "result = df['v'].mean()"]
    )
    monkeypatch.setattr(nodes, "LLMClient", lambda: scripted)

    final = agentic_ai.invoke(_state(_csv))

    assert final["status"] == "completed"
    assert final["steps_taken"] > 1            # took more than one attempt
    assert final["exec_result"] == 20.0


def test_step_cap_yields_failed_with_error_and_last_code(monkeypatch, _csv):
    # Every attempt errors -> cap hit.
    scripted = _ScriptedLLM(["result = df['nope'].mean()"] * 10)
    monkeypatch.setattr(nodes, "LLMClient", lambda: scripted)

    final = agentic_ai.invoke(_state(_csv, max_steps=3))

    assert final["status"] == "failed"
    assert final["error_message"]
    assert "nope" in final["code"]             # last attempted code preserved
    assert final["steps_taken"] == 3
