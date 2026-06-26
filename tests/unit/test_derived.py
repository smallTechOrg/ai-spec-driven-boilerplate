"""Offline, deterministic tests for slice-4a derived datasets (C25 + C15).

No LLM, no network. These exercise the *deterministic* machinery directly:

- `register_derived_dataset` writes the CSV + Parquet and inserts a `datasets`
  row with full lineage (`origin="derived"`, parents, run id, derivation code).
- `is_stale` flips True once a parent's `updated_at` moves past the derived
  dataset's `created_at`.
- `POST /datasets/{id}/re-derive` on a non-derived dataset returns 400
  `not_derived`; on a real derived dataset it re-runs the code and clears stale.
- `DELETE /datasets/{parent}` recursively deletes derived children (C15).

The uploads dir is monkeypatched to a tmp dir for BOTH `graph.derived` and the
name `api.datasets._uploads_dir` (datasets.py imports the function by reference).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from db.models import DatasetRow
from db.session import create_db_session


@pytest.fixture
def uploads_dir(tmp_path, monkeypatch):
    """Point the derived/registration + datasets-route uploads dir at a tmp dir."""
    import api.datasets as datasets_module
    import graph.derived as derived_module

    d = tmp_path / "uploads"
    d.mkdir()
    monkeypatch.setattr(derived_module, "_uploads_dir", lambda: d)
    # datasets.py imported `_uploads_dir` by reference — patch that name too.
    monkeypatch.setattr(datasets_module, "_uploads_dir", lambda: d)
    return d


def _make_parent(filename: str, df: pd.DataFrame, uploads_dir=None) -> str:
    """Insert an uploaded parent dataset row.

    When `uploads_dir` is given, also writes the on-disk CSV + Parquet so the
    re-derive route can load it (mirrors a real upload into the tmp uploads dir).
    """
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
        if uploads_dir is not None:
            csv_path = uploads_dir / f"{dataset_id}.csv"
            df.to_csv(csv_path, index=False)
            df.to_parquet(uploads_dir / f"{dataset_id}.parquet", index=False)
            row.file_path = str(csv_path)
            row.parquet_path = str(uploads_dir / f"{dataset_id}.parquet")
        return dataset_id


# --------------------------------------------------------------------------- #
# _extract_derivation_expr — recover the df expression from a save_dataset call
# --------------------------------------------------------------------------- #


def test_extract_derivation_expr_unwraps_save_dataset():
    from graph.sandbox import _extract_derivation_expr

    assert (
        _extract_derivation_expr("save_dataset(df.dropna(), 'cleaned', 'desc')")
        == "df.dropna()"
    )
    # Nested parens in the first argument are preserved.
    assert (
        _extract_derivation_expr("save_dataset(df[df['a'] > df['a'].mean()], 'big')")
        == "df[df['a'] > df['a'].mean()]"
    )
    # A comma inside a string in the name arg does not truncate the df expr.
    assert (
        _extract_derivation_expr("save_dataset(df.head(3), 'a, b', 'note')")
        == "df.head(3)"
    )
    # A bare (non-call) expression is returned unchanged.
    assert _extract_derivation_expr("df.dropna()") == "df.dropna()"


# --------------------------------------------------------------------------- #
# register_derived_dataset — row + files + lineage
# --------------------------------------------------------------------------- #


def test_register_derived_writes_files_and_lineage(uploads_dir):
    from graph.derived import register_derived_dataset

    parent_id = _make_parent("source.csv", pd.DataFrame({"a": [1, 2, None]}))
    df = pd.DataFrame({"a": [1, 2]})

    new_id = register_derived_dataset(
        df,
        "cleaned",
        "nulls dropped",
        run_id="run-123",
        parent_ids=[parent_id],
        derivation_code="df.dropna()",
    )

    # Files exist on disk.
    assert (uploads_dir / f"{new_id}.csv").exists()
    assert (uploads_dir / f"{new_id}.parquet").exists()

    # Row exists with full lineage.
    with create_db_session() as session:
        row = session.get(DatasetRow, new_id)
        assert row is not None
        assert row.origin == "derived"
        assert row.derived_from_run_id == "run-123"
        assert row.derived_from_dataset_ids == [parent_id]
        assert row.derivation_code == "df.dropna()"
        assert row.row_count == 2
        assert row.col_count == 1
        assert row.content_hash  # sha256 of the CSV bytes, non-empty
        assert row.filename == "cleaned.csv"
        assert row.context == "nulls dropped"
        # The on-disk CSV round-trips to the same data.
        round_trip = pd.read_csv(uploads_dir / f"{new_id}.csv")
        assert list(round_trip["a"]) == [1, 2]


def test_register_derived_rejects_non_dataframe(uploads_dir):
    from graph.derived import register_derived_dataset

    with pytest.raises(TypeError):
        register_derived_dataset(
            [1, 2, 3], "bad", run_id="r", parent_ids=[], derivation_code="x"
        )


# --------------------------------------------------------------------------- #
# is_stale — flips when a parent changes after derivation
# --------------------------------------------------------------------------- #


def test_is_stale_flips_after_parent_touched(uploads_dir):
    from graph.derived import is_stale, register_derived_dataset

    parent_id = _make_parent("p.csv", pd.DataFrame({"a": [1, 2, 3]}))
    new_id = register_derived_dataset(
        pd.DataFrame({"a": [1, 2]}),
        "child",
        run_id="r1",
        parent_ids=[parent_id],
        derivation_code="df.head(2)",
    )

    with create_db_session() as session:
        child = session.get(DatasetRow, new_id)
        # Fresh derivation: not stale.
        assert is_stale(child, session) is False

    # Touch the parent's updated_at to AFTER the child's created_at.
    with create_db_session() as session:
        child = session.get(DatasetRow, new_id)
        parent = session.get(DatasetRow, parent_id)
        parent.updated_at = child.created_at + timedelta(seconds=10)

    with create_db_session() as session:
        child = session.get(DatasetRow, new_id)
        assert is_stale(child, session) is True


def test_is_stale_false_for_uploaded(uploads_dir):
    from graph.derived import is_stale

    parent_id = _make_parent("p2.csv", pd.DataFrame({"a": [1]}))
    with create_db_session() as session:
        row = session.get(DatasetRow, parent_id)
        assert is_stale(row, session) is False


# --------------------------------------------------------------------------- #
# /re-derive route — 400 not_derived, and a real re-derive clears stale
# --------------------------------------------------------------------------- #


def test_re_derive_non_derived_returns_400(api_client, uploads_dir):
    # An uploaded (non-derived) dataset has no derivation code.
    dataset_id = _make_parent("nums.csv", pd.DataFrame({"a": [1, 2, 3]}))

    r = api_client.post(f"/datasets/{dataset_id}/re-derive")
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["code"] == "not_derived"


def test_re_derive_404_when_missing(api_client, uploads_dir):
    r = api_client.post("/datasets/ghost/re-derive")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "not_found"


def test_re_derive_runs_code_and_clears_stale(api_client, uploads_dir):
    """A derived dataset re-runs `df.dropna()` against the CURRENT parent and is
    no longer stale afterwards."""
    from graph.derived import register_derived_dataset

    # A parent with one null row, written into the tmp uploads dir the re-derive
    # route reads from.
    parent_df = pd.DataFrame({"a": [1.0, 2.0, None], "b": ["x", "y", "z"]})
    parent_id = _make_parent("src.csv", parent_df, uploads_dir=uploads_dir)

    # Register a derived dataset (df.dropna()) from the current parent.
    derived_id = register_derived_dataset(
        parent_df.dropna(),
        "cleaned",
        run_id="r1",
        parent_ids=[parent_id],
        derivation_code="df.dropna()",
    )

    # Make the child stale: backdate its created_at to BEFORE the parent's
    # updated_at (i.e. the parent changed after derivation). This mirrors a real
    # "parent edited after the derived dataset was produced" without fabricating a
    # future timestamp the wall-clock-based re-derive could not surpass.
    with create_db_session() as session:
        child = session.get(DatasetRow, derived_id)
        parent = session.get(DatasetRow, parent_id)
        child.created_at = parent.updated_at - timedelta(seconds=30)

    listing = api_client.get("/datasets").json()["data"]
    child_item = next(d for d in listing if d["id"] == derived_id)
    assert child_item["stale"] is True
    assert child_item["origin"] == "derived"
    assert parent_id in child_item["derived_from_dataset_ids"]

    # Re-derive: re-runs df.dropna() vs the current parent, clears stale.
    r = api_client.post(f"/datasets/{derived_id}/re-derive")
    assert r.status_code == 200, r.text
    item = r.json()["data"]
    assert item["stale"] is False
    # df.dropna() over 3 rows (one with a null) -> 2 rows.
    assert item["row_count"] == 2

    # And the listing now reports not-stale too.
    listing2 = api_client.get("/datasets").json()["data"]
    child_item2 = next(d for d in listing2 if d["id"] == derived_id)
    assert child_item2["stale"] is False


def test_re_derive_parent_not_found(api_client, uploads_dir):
    from graph.derived import register_derived_dataset

    derived_id = register_derived_dataset(
        pd.DataFrame({"a": [1]}),
        "orphan",
        run_id="r1",
        parent_ids=["ghost-parent"],
        derivation_code="df.head(1)",
    )
    r = api_client.post(f"/datasets/{derived_id}/re-derive")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "parent_not_found"


# --------------------------------------------------------------------------- #
# Recursive cascade delete (C15)
# --------------------------------------------------------------------------- #


def test_delete_parent_cascades_to_derived_child(api_client, uploads_dir):
    from graph.derived import register_derived_dataset

    parent_id = _make_parent(
        "base.csv", pd.DataFrame({"a": [1, 2]}), uploads_dir=uploads_dir
    )

    child_id = register_derived_dataset(
        pd.DataFrame({"a": [1]}),
        "child",
        run_id="r1",
        parent_ids=[parent_id],
        derivation_code="df.head(1)",
    )
    grandchild_id = register_derived_dataset(
        pd.DataFrame({"a": [1]}),
        "grandchild",
        run_id="r2",
        parent_ids=[child_id],
        derivation_code="df.head(1)",
    )

    # All three present.
    ids_before = {d["id"] for d in api_client.get("/datasets").json()["data"]}
    assert {parent_id, child_id, grandchild_id} <= ids_before

    # Delete the parent -> child AND grandchild go too (transitive).
    r = api_client.delete(f"/datasets/{parent_id}")
    assert r.status_code == 200, r.text
    deleted = set(r.json()["data"]["derived_deleted"])
    assert child_id in deleted
    assert grandchild_id in deleted

    ids_after = {d["id"] for d in api_client.get("/datasets").json()["data"]}
    assert parent_id not in ids_after
    assert child_id not in ids_after
    assert grandchild_id not in ids_after
    # Files removed too.
    assert not (uploads_dir / f"{child_id}.csv").exists()
    assert not (uploads_dir / f"{grandchild_id}.parquet").exists()


# --------------------------------------------------------------------------- #
# Session cascade on dataset delete (C15)
# --------------------------------------------------------------------------- #


def _make_session(dataset_id=None, dataset_ids=None, name=None) -> str:
    """Insert a conversation_sessions row referencing dataset(s); return its id."""
    from db.models import ConversationSessionRow

    with create_db_session() as session:
        row = ConversationSessionRow(
            dataset_id=dataset_id,
            dataset_ids_json=dataset_ids,
            name=name,
        )
        session.add(row)
        session.flush()
        return row.id


def _session_ids() -> set[str]:
    from db.models import ConversationSessionRow
    from sqlalchemy import select

    with create_db_session() as session:
        return {s.id for s in session.execute(select(ConversationSessionRow)).scalars().all()}


def test_delete_dataset_cascades_to_referencing_sessions(api_client, uploads_dir):
    """C15: deleting a dataset removes every session that references it.

    Covers both reference shapes: the single `dataset_id` column AND the
    `dataset_ids_json` multi-dataset list. A session referencing only OTHER
    datasets must survive.
    """
    target_id = _make_parent("target.csv", pd.DataFrame({"a": [1, 2]}), uploads_dir=uploads_dir)
    other_id = _make_parent("other.csv", pd.DataFrame({"b": [3, 4]}), uploads_dir=uploads_dir)

    # Single-dataset session on the target.
    sess_single = _make_session(dataset_id=target_id, name="single")
    # Multi-dataset session whose list contains the target.
    sess_multi = _make_session(dataset_ids=[other_id, target_id], name="multi")
    # A session on a DIFFERENT dataset only — must survive the delete.
    sess_unrelated = _make_session(dataset_id=other_id, name="unrelated")

    assert {sess_single, sess_multi, sess_unrelated} <= _session_ids()

    r = api_client.delete(f"/datasets/{target_id}")
    assert r.status_code == 200, r.text

    remaining = _session_ids()
    assert sess_single not in remaining  # single-column reference removed
    assert sess_multi not in remaining  # list-membership reference removed
    assert sess_unrelated in remaining  # unrelated session preserved


def test_delete_all_datasets_removes_all_sessions(api_client, uploads_dir):
    """C15: clearing the data universe removes every conversation session too."""
    ds_a = _make_parent("a.csv", pd.DataFrame({"a": [1]}), uploads_dir=uploads_dir)
    ds_b = _make_parent("b.csv", pd.DataFrame({"b": [2]}), uploads_dir=uploads_dir)

    s1 = _make_session(dataset_id=ds_a)
    s2 = _make_session(dataset_ids=[ds_a, ds_b])
    assert {s1, s2} <= _session_ids()

    r = api_client.delete("/datasets")
    assert r.status_code == 200, r.text

    assert _session_ids() == set()  # no sessions left once the universe is cleared
