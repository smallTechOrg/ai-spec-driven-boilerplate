"""Real-Gemini integration test for derived-dataset persistence (C25, slice-4a).

Requires `AGENT_GEMINI_API_KEY` in `.env` (auto-detect selects the real Gemini
provider). The agent is asked to clean the data (drop null rows) and persist it
with `save_dataset` — the run must register a NEW `origin="derived"` dataset with
correct lineage (parents, producing run id, derivation code) and write its
CSV + Parquet to disk.

Driven via `run_agent(..., run_selector=True, skip_clarification=True)` against
the production SQLite driver (the isolated copy via `_isolated_db`). The uploads
dir is monkeypatched for nodes, runner, AND `graph.derived` (the registration
writes through `graph.derived._uploads_dir`). Asserts CONTENT — a real derived
row with populated lineage and on-disk files.
"""
from __future__ import annotations

import pandas as pd
import pytest

from db.models import DatasetRow
from db.session import create_db_session
from graph import nodes as nodes_module
from graph.runner import run_agent


@pytest.fixture(autouse=True)
def uploads_dir(tmp_path, monkeypatch):
    """Point nodes', runner's, AND derived's uploads dir at a tmp dir."""
    import graph.derived as derived_module
    import graph.runner as runner_module

    d = tmp_path / "uploads"
    d.mkdir()
    monkeypatch.setattr(nodes_module, "_uploads_dir", lambda: d)
    monkeypatch.setattr(runner_module, "_uploads_dir", lambda: d)
    monkeypatch.setattr(derived_module, "_uploads_dir", lambda: d)
    return d


@pytest.fixture(autouse=True)
def _clear_session_cache():
    nodes_module._session_cache.clear()
    yield
    nodes_module._session_cache.clear()


def _make_dataset(uploads_dir, filename: str, df: pd.DataFrame) -> str:
    with create_db_session() as session:
        row = DatasetRow(
            filename=filename,
            file_path="",
            row_count=len(df),
            col_count=len(df.columns),
            columns_json=[{"name": str(c), "dtype": str(df[c].dtype)} for c in df.columns],
            content_hash=f"hash-{filename}",
            format="csv",
            origin="uploaded",
        )
        session.add(row)
        session.flush()
        dataset_id = row.id
        csv_path = uploads_dir / f"{dataset_id}.csv"
        df.to_csv(csv_path, index=False)
        df.to_parquet(uploads_dir / f"{dataset_id}.parquet")
        row.file_path = str(csv_path)
    return dataset_id


@pytest.mark.usefixtures("_require_llm_key")
def test_real_gemini_save_dataset_registers_derived(uploads_dir):
    """Ask the real model to drop null rows and save the result with
    save_dataset -> a NEW derived dataset is registered with full lineage."""
    df = pd.DataFrame(
        {
            "name": ["a", "b", "c", "d", "e", "f"],
            "score": [10.0, None, 30.0, None, 50.0, 60.0],
            "grade": ["x", "y", "z", "p", "q", "r"],
        }
    )
    parent_id = _make_dataset(uploads_dir, "scores.csv", df)

    question = (
        "Create a cleaned copy of this data with null rows dropped and save it as "
        "'cleaned' using save_dataset. Concretely, run "
        "save_dataset(df.dropna(), 'cleaned', 'rows with nulls removed') and then "
        "give your FINAL ANSWER confirming how many rows remain."
    )
    result = run_agent(
        question,
        [parent_id],
        run_selector=True,
        skip_clarification=True,
    )

    assert result["type"] == "answer", f"expected an answer, got {result.get('type')}"
    run_id = result["run_id"]

    derived_ids = result["derived_dataset_ids"]
    assert isinstance(derived_ids, list)
    assert derived_ids, (
        "expected at least one derived dataset id in the result; "
        f"steps={[s.get('action') for s in result.get('action_history', [])]}"
    )
    derived_id = derived_ids[0]

    # A NEW origin=derived row exists with correct lineage.
    with create_db_session() as session:
        derived_rows = (
            session.query(DatasetRow).filter(DatasetRow.origin == "derived").all()
        )
        assert derived_rows, "no derived dataset row was created"
        row = session.get(DatasetRow, derived_id)
        assert row is not None
        assert row.origin == "derived"
        assert parent_id in (row.derived_from_dataset_ids or []), (
            f"derived lineage should include the parent {parent_id}; "
            f"got {row.derived_from_dataset_ids}"
        )
        assert row.derived_from_run_id == run_id, (
            f"derived_from_run_id should be {run_id}; got {row.derived_from_run_id}"
        )
        assert (row.derivation_code or "").strip(), "derivation_code must be non-empty"
        lineage_parents = list(row.derived_from_dataset_ids or [])
        lineage_run = row.derived_from_run_id
        lineage_code = row.derivation_code

    # The on-disk files exist.
    assert (uploads_dir / f"{derived_id}.csv").exists(), "derived CSV not written"
    assert (uploads_dir / f"{derived_id}.parquet").exists(), "derived Parquet not written"

    print(f"\n[derived] new derived dataset id: {derived_id}")
    print(f"[derived] derived_from_dataset_ids: {lineage_parents}")
    print(f"[derived] derived_from_run_id: {lineage_run}")
    print(f"[derived] derivation_code[:80]: {(lineage_code or '')[:80]!r}")
