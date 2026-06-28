"""PRIVACY BOUNDARY GATE — runs against real Gemini via .env.

Loads a dataset whose raw rows contain DISTINCTIVE SENTINEL values, large enough
that the answer must come from aggregation (a sample != the full set). Records
EVERY prompt string sent to the Gemini provider, runs a real ask end-to-end, and
asserts:
  (a) NO sentinel raw-row value appears in ANY captured prompt; and
  (b) query_rows was non-empty (the data really was queried locally).

This proves the boundary structurally — raw rows are queried locally but never
cross to the LLM.
"""
import json

import pytest
from sqlalchemy.orm import Session

from data.ingest import ingest_file
from db.models import Dataset
from db import session as session_module


# Number of distinct sentinel rows — far larger than any plausible sample window.
_N_ROWS = 600


def _sentinel_csv() -> bytes:
    """Each row carries a globally-unique sentinel token in a free-text cell.

    The sentinel tokens are highly distinctive so any leak into a prompt is
    unambiguous. Tier totals are knowable only from the full data.
    """
    lines = ["customer,tier,revenue,secret_note"]
    for i in range(_N_ROWS):
        tier = ["gold", "silver", "bronze"][i % 3]
        # revenue chosen so gold tier clearly leads in total
        rev = {"gold": 1000, "silver": 100, "bronze": 10}[tier]
        token = f"ZZSENTINEL{i:04d}QQ"
        lines.append(f"{token},{tier},{rev},note_{token}")
    return ("\n".join(lines) + "\n").encode("utf-8")


@pytest.mark.usefixtures("_require_llm_key")
def test_no_raw_row_value_reaches_any_gemini_prompt(_isolated_db, tmp_path, monkeypatch):
    # Capture every prompt string + system prompt sent through the LLM client.
    captured: list[str] = []
    from llm.client import LLMClient

    real = LLMClient.call_model_usage

    def _spy(self, prompt, *, system=None):
        captured.append(prompt or "")
        if system:
            captured.append(system)
        return real(self, prompt, system=system)

    monkeypatch.setattr(LLMClient, "call_model_usage", _spy)

    # Ingest the sentinel dataset and register it.
    datasets = ingest_file(
        filename="sentinels.csv", content=_sentinel_csv(), storage_dir=tmp_path
    )
    d = datasets[0]
    with Session(_isolated_db) as s:
        s.add(
            Dataset(
                id=d.id, name=d.name, source_path=d.source_path,
                source_kind=d.source_kind, sheet_name=d.sheet_name,
                duckdb_table=d.duckdb_table,
                profile_json=json.dumps(d.profile), row_count=d.row_count,
                size_bytes=d.size_bytes,
            )
        )
        s.commit()

    from graph.runner import ask

    response = ask(d.id, "What is the total revenue for each tier?")

    # The run must have actually executed and produced an answer.
    assert response.status == "completed", response.error
    assert captured, "no prompts were captured — the LLM was never called"

    # (a) No sentinel raw-row value appears in ANY captured prompt.
    joined = "\n".join(captured)
    assert "ZZSENTINEL" not in joined, (
        "a raw-row sentinel value leaked into an LLM prompt — privacy boundary breached"
    )
    assert "note_" not in joined, "a raw free-text cell leaked into an LLM prompt"

    # (b) Prove data was really queried locally (not an empty/trivial path):
    # re-run the exact generated SQL locally and confirm non-empty rows.
    from data.duckdb_engine import duckdb_query
    rows, _ = duckdb_query(response.generated_sql, d.ref())
    assert rows, "query returned no rows — boundary not actually exercised"

    # And the aggregate answer must reflect the FULL data: gold tier total is the
    # max and equals 200 rows * 1000 = 200000 (knowable only from all rows).
    totals = {r.get("tier"): list(r.values()) for r in rows}
    # whichever column is the numeric total, gold's total must be the largest
    numeric_totals = {}
    for r in rows:
        tier = r.get("tier")
        for k, v in r.items():
            if k != "tier" and isinstance(v, (int, float)):
                numeric_totals[tier] = v
    assert numeric_totals.get("gold") == max(numeric_totals.values())
    assert numeric_totals["gold"] == 200 * 1000


@pytest.mark.usefixtures("_require_llm_key")
def test_row_level_question_does_not_leak_raw_cells(_isolated_db, tmp_path, monkeypatch):
    """The HARD case: a ROW-RETURNING question (e.g. "show the largest orders").

    The correct SQL for this returns RAW rows whose cells carry unique sentinel
    PII / free-text. The aggregate gate must summarize them locally so NO sentinel
    value reaches any Gemini prompt, while data really was queried locally.

    This assertion FAILS against a gate that merely caps-and-passes raw rows, and
    PASSES against a gate that structurally summarizes them.
    """
    captured: list[str] = []
    from llm.client import LLMClient

    real = LLMClient.call_model_usage

    def _spy(self, prompt, *, system=None):
        captured.append(prompt or "")
        if system:
            captured.append(system)
        return real(self, prompt, system=system)

    monkeypatch.setattr(LLMClient, "call_model_usage", _spy)

    datasets = ingest_file(
        filename="sentinels.csv", content=_sentinel_csv(), storage_dir=tmp_path
    )
    d = datasets[0]
    with Session(_isolated_db) as s:
        s.add(
            Dataset(
                id=d.id, name=d.name, source_path=d.source_path,
                source_kind=d.source_kind, sheet_name=d.sheet_name,
                duckdb_table=d.duckdb_table,
                profile_json=json.dumps(d.profile), row_count=d.row_count,
                size_bytes=d.size_bytes,
            )
        )
        s.commit()

    from graph.runner import ask

    # A deliberately row-level ask: the natural SQL returns individual rows whose
    # cells include the unique sentinel customer + secret_note values.
    response = ask(
        d.id,
        "Show me the individual customers with the largest revenue, "
        "including their secret_note, one row per customer.",
    )

    assert response.status == "completed", response.error
    assert captured, "no prompts were captured — the LLM was never called"

    # The raw query for this row-level question really returns rows with sentinels.
    from data.duckdb_engine import duckdb_query
    rows, _ = duckdb_query(response.generated_sql, d.ref())
    assert rows, "row-level query returned no rows — boundary not exercised"
    sentinel_rows = [
        r for r in rows
        if any(isinstance(v, str) and "ZZSENTINEL" in v for v in r.values())
    ]
    assert sentinel_rows, (
        "the generated SQL did not actually return rows carrying sentinel cells; "
        "the hard case was not exercised"
    )

    # No sentinel raw-row value may appear in ANY captured prompt.
    joined = "\n".join(captured)
    assert "ZZSENTINEL" not in joined, (
        "a raw-row sentinel value leaked into an LLM prompt on a row-level "
        "question — privacy boundary breached"
    )
    assert "note_" not in joined, "a raw free-text cell leaked into an LLM prompt"
