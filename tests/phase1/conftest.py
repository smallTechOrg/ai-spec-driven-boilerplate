"""Shared fixtures for Phase-1 tests.

Builds a multi-thousand-row CSV whose answer over the FULL data differs
observably from any answer a <=5-row sample would give (proves full-data
computation), and a spy that captures every prompt sent to the LLM client.
"""
import csv

import pytest

# A high-cardinality free-text cell value that exists ONLY in a row far beyond
# the <=5-row sample window. It is NOT a top-5 categorical (the `note` column is
# unique per row) and NOT a numeric extremum, so the ONLY way it could reach the
# LLM is by serializing a raw data row — which the privacy invariant forbids.
SENTINEL_NOTE = "ZZ_SENTINEL_ONLY_IN_DEEP_ROW_Q7X"


@pytest.fixture
def big_csv(tmp_path):
    """A ~4000-row sales CSV with known per-region totals + a deep-row sentinel.

    First 5 rows are all region 'West' with small revenue, so a sampled-only
    computation would miss every other region entirely. The `note` column is
    unique per row (high-cardinality) and carries the sentinel only at row ~2000.
    """
    path = tmp_path / "sales.csv"
    rows = []

    # First 5 rows: all West, tiny revenue (the sample window).
    for i in range(5):
        rows.append({"region": "West", "revenue": 1, "note": f"intro-{i}"})

    # Bulk rows: deterministic totals across four regions, unique notes.
    regions = ["West", "East", "North", "South"]
    for i in range(4000):
        region = regions[i % 4]
        note = SENTINEL_NOTE if i == 2000 else f"row-{i}"
        rows.append({"region": region, "revenue": 10, "note": note})

    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["region", "revenue", "note"])
        w.writeheader()
        w.writerows(rows)

    return path


@pytest.fixture
def llm_spy(monkeypatch):
    """Wrap LLMClient.call_model so every prompt/system sent is captured.

    Returns a list that accumulates dicts {"prompt", "system"} for assertions.
    The real Gemini API is still called (we wrap, not replace).
    """
    import llm.client as client_module

    captured: list[dict] = []
    original = client_module.LLMClient.call_model

    def _spy(self, prompt, *, system=None):
        captured.append({"prompt": prompt, "system": system})
        return original(self, prompt, system=system)

    monkeypatch.setattr(client_module.LLMClient, "call_model", _spy)
    return captured
