"""Integration test — real Gemini end-to-end through the runner (no HTTP layer).

Exercises run_ask: builds state from a real Dataset row, runs the graph against
the real LLM + local executor over ALL rows, persists the Turn, and returns the
response data. Asserts the privacy-safe full-data path and SSE step callback.
"""

import csv

import pytest
from sqlalchemy.orm import Session

from db.models import Dataset, Turn
from analysis.profiler import profile_csv
from graph.runner import run_ask

# Skewed fixture: first 300 rows are all NW (poisons any first-N-row sample),
# remaining rows distributed so the true full-data counts differ sharply from
# the sample. Lets us assert COMPUTED VALUES, not just shape.
TRUE_REGION_COUNTS = {"NW": 300, "SE": 2500, "SW": 2700, "NE": 1500}
TOTAL_ROWS = sum(TRUE_REGION_COUNTS.values())  # 7000


def _write_csv(path, rows: int = TOTAL_ROWS) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["region", "amount"])
        amount = 0
        for _ in range(300):
            w.writerow(["NW", amount])
            amount += 1
        for region, n in {"SE": 2500, "SW": 2700, "NE": 1500}.items():
            for _ in range(n):
                w.writerow([region, amount])
                amount += 1


def _result_table_to_region_counts(result_table: list) -> dict:
    """Parse a bare-rows result_table into {region: count}, robust to the
    LLM naming the count column differently."""
    assert result_table, "result_table must be non-empty"
    keys = list(result_table[0].keys())
    known = set(TRUE_REGION_COUNTS)

    region_col = next(
        (k for k in keys
         if {str(r.get(k)) for r in result_table} & known),
        None,
    )
    assert region_col is not None, f"no region-like column in {keys}"

    def _coerce_int(v):
        try:
            return int(round(float(v)))
        except (TypeError, ValueError):
            return None

    count_col = next(
        (k for k in keys
         if k != region_col
         and all(_coerce_int(r.get(k)) is not None for r in result_table)),
        None,
    )
    assert count_col is not None, f"no count-like column in {keys}"
    return {
        str(r[region_col]): _coerce_int(r[count_col]) for r in result_table
    }


@pytest.mark.usefixtures("_require_llm_key")
def test_run_ask_end_to_end(_isolated_db, tmp_path):
    csv_path = tmp_path / "data.csv"
    _write_csv(csv_path)
    profiled = profile_csv(str(csv_path))
    assert profiled["row_count"] == TOTAL_ROWS  # full-file count (7000)

    with Session(_isolated_db) as s:
        ds = Dataset(
            name="data.csv",
            file_path=str(csv_path),
            source_kind="csv",
            row_count=profiled["row_count"],
            column_count=profiled["column_count"],
            profile=profiled["profile"],
            sample_rows=profiled["sample_rows"],
        )
        s.add(ds)
        s.commit()
        dataset_id = ds.id

    steps = []
    data = run_ask(
        dataset_id, None, "how many rows per region?",
        on_step=lambda step, status: steps.append((step, status)),
    )

    assert steps, "expected step callbacks during the run"
    assert data["answer"].strip()
    assert data["code"].strip()
    assert data["token_usage"]["total"] > 0

    # VALUE assertion: counts computed over ALL rows, not the first-N sample
    # (a sample of the first 200 rows would report {"NW": 200} only).
    got = _result_table_to_region_counts(data["result_table"])
    assert got == TRUE_REGION_COUNTS, (
        f"run_ask returned sample/truncated counts {got}, "
        f"expected full-data {TRUE_REGION_COUNTS}"
    )

    with Session(_isolated_db) as s:
        turn = s.get(Turn, data["turn_id"])
        assert turn is not None
        assert turn.status == "completed"
        assert turn.conversation_id == data["conversation_id"]
