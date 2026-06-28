"""End-to-end primary journey over the REAL FastAPI app + REAL Gemini.

Uploads a >=5,000-row CSV, asks a question (consuming the live SSE stream),
asserts a correct local answer + code + chart + token usage, that the Turn was
persisted as completed, then asks a FOLLOW-UP with the conversation_id and
confirms context carries. Asserts the response shape matches the frontend
contract EXACTLY.
"""

import csv
import io
import json
import random
import re

import pandas as pd
import pytest

# Skewed fixture: the first 300 rows are ALL region="NW", so a sample of the
# first 200 rows would report 100% NW and miss every other region entirely.
# The full data has very different per-region counts. A test that only asserts
# SHAPE (non-empty table) would pass even if the executor computed over the
# sample; we assert the TRUE full-data counts so a wrong-value regression fails.
TRUE_REGION_COUNTS = {"NW": 300, "SE": 2500, "SW": 2700, "NE": 1500}
ROWS = sum(TRUE_REGION_COUNTS.values())  # 7000


def _make_csv() -> bytes:
    """Build a CSV whose first 300 rows are all NW, then the remaining regions.

    Engineered so the first-200-row sample (all NW) disagrees with the true
    full-data per-region counts.
    """
    random.seed(42)
    rows = []
    # First 300 rows: all NW (poisons any first-N-row sample).
    for _ in range(300):
        rows.append(["NW", round(random.uniform(1, 1000), 2),
                     random.choice(["A", "B", "C"])])
    # Remaining rows distributed to hit the true counts above.
    remaining = {"SE": 2500, "SW": 2700, "NE": 1500}
    for region, n in remaining.items():
        for _ in range(n):
            rows.append([region, round(random.uniform(1, 1000), 2),
                         random.choice(["A", "B", "C"])])
    assert len(rows) == ROWS

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["region", "amount", "category"])
    w.writerows(rows)
    return buf.getvalue().encode()


def _expected_region_counts(csv_bytes: bytes) -> dict:
    """Compute the ground-truth per-region counts directly with pandas."""
    df = pd.read_csv(io.BytesIO(csv_bytes))
    return df.groupby("region").size().to_dict()


def _result_table_to_region_counts(result_table: list) -> dict:
    """Parse a bare-rows result_table into {region: count}.

    Robust to LLM column-name variation: the category column is whichever
    column holds the region labels (matches our known regions); the count
    column is whichever remaining column holds integer-like values.
    """
    assert result_table, "result_table must be non-empty"
    keys = list(result_table[0].keys())
    known = set(TRUE_REGION_COUNTS)

    def _is_region_col(col):
        vals = {str(row.get(col)) for row in result_table}
        return bool(vals & known)

    region_col = next((k for k in keys if _is_region_col(k)), None)
    assert region_col is not None, f"no region-like column in {keys}"

    def _coerce_int(v):
        try:
            return int(round(float(v)))
        except (TypeError, ValueError):
            return None

    count_col = None
    for k in keys:
        if k == region_col:
            continue
        if all(_coerce_int(row.get(k)) is not None for row in result_table):
            count_col = k
            break
    assert count_col is not None, f"no count-like column in {keys}"

    return {
        str(row[region_col]): _coerce_int(row[count_col])
        for row in result_table
    }


def _parse_sse(text: str):
    """Return (step_events, final_data) from an SSE body."""
    steps, final = [], None
    for frame in text.split("\n\n"):
        frame = frame.strip()
        if not frame:
            continue
        line = frame[len("data: "):] if frame.startswith("data: ") else frame
        payload = json.loads(line)
        if "step" in payload:
            steps.append(payload)
        elif "data" in payload:
            final = payload
    return steps, final


def _assert_contract_shape(data: dict):
    """Exact frontend AnswerData contract (frontend/src/lib/api.ts)."""
    assert isinstance(data["turn_id"], str) and data["turn_id"]
    assert isinstance(data["conversation_id"], str) and data["conversation_id"]
    assert isinstance(data["answer"], str)
    assert isinstance(data["plan"], list)
    assert isinstance(data["code"], str)
    assert isinstance(data["result_table"], list)  # bare rows array
    assert data["chart_spec"] is None or isinstance(data["chart_spec"], dict)
    assert isinstance(data["follow_ups"], list)
    tu = data["token_usage"]
    assert set(tu) == {"prompt", "completion", "total"}
    assert tu["total"] == tu["prompt"] + tu["completion"]
    assert isinstance(data["estimated_cost_usd"], (int, float))
    assert isinstance(data["assumptions"], list)


@pytest.mark.usefixtures("_require_llm_key")
def test_primary_journey_upload_ask_followup(api_client, _isolated_db):
    csv_bytes = _make_csv()
    # Ground truth computed directly with pandas over ALL rows.
    expected = _expected_region_counts(csv_bytes)
    assert expected == TRUE_REGION_COUNTS, expected  # fixture sanity check

    # --- Upload + profile over ALL rows ---
    up = api_client.post(
        "/datasets", files={"file": ("sales.csv", csv_bytes, "text/csv")}
    )
    assert up.status_code == 200, up.text
    ds = up.json()["data"]
    assert ds["row_count"] == ROWS  # full-file count, not a sample
    assert ds["column_count"] == 3
    dataset_id = ds["dataset_id"]

    # --- Ask (consume the live SSE stream) ---
    r = api_client.post(
        f"/datasets/{dataset_id}/ask",
        json={"question": "how many rows per region?"},
    )
    assert r.status_code == 200, r.text
    assert "text/event-stream" in r.headers["content-type"]
    steps, final = _parse_sse(r.text)
    assert steps, "expected live step events"
    assert final is not None, "expected a final answer envelope"
    assert final.get("error") is None, final

    data = final["data"]
    _assert_contract_shape(data)
    assert data["answer"].strip(), "expected a real answer string"
    assert data["code"].strip(), "expected code to be shown"
    assert data["result_table"], "expected a non-empty result table"
    assert data["chart_spec"] is not None, "expected a chart spec"
    assert data["token_usage"]["total"] > 0

    # --- VALUE assertion: full-data per-region counts, NOT the sample ---
    # A sample of the first 200 rows would yield {"NW": 200} only. The
    # executor must compute over ALL rows, so we assert the TRUE counts.
    got_counts = _result_table_to_region_counts(data["result_table"])
    assert got_counts == TRUE_REGION_COUNTS, (
        f"executor returned sample/truncated counts {got_counts}, "
        f"expected full-data {TRUE_REGION_COUNTS}"
    )

    conversation_id = data["conversation_id"]
    first_turn_id = data["turn_id"]

    # --- Turn persisted as completed ---
    from sqlalchemy.orm import Session
    from db.models import Turn

    with Session(_isolated_db) as s:
        turn = s.get(Turn, first_turn_id)
        assert turn is not None
        assert turn.status == "completed"
        assert turn.error_message is None
        assert (turn.prompt_tokens or 0) + (turn.completion_tokens or 0) > 0

    # --- Follow-up using the conversation_id (context carries) ---
    r2 = api_client.post(
        f"/datasets/{dataset_id}/ask",
        json={"question": "what about just NW? give me the count",
              "conversation_id": conversation_id},
    )
    assert r2.status_code == 200, r2.text
    _, final2 = _parse_sse(r2.text)
    assert final2 is not None and final2.get("error") is None, final2
    data2 = final2["data"]
    _assert_contract_shape(data2)
    assert data2["conversation_id"] == conversation_id  # same conversation
    assert data2["turn_id"] != first_turn_id
    assert data2["answer"].strip()

    # --- Context-carry VALUE assertion ---
    # "what about just NW?" carries no dataset noun — it only makes sense if the
    # prior turn's context ("rows per region") was applied. The deterministic NW
    # full-data count (300) must therefore surface, proving context carried.
    #
    # We are tolerant of how the LLM realises "just NW": it may return a
    # one-region count table ([{region:"NW", count:300}] or [{"value":300}]) OR
    # describe the count in prose. Either way the number 300 must appear. We do
    # NOT over-constrain the table to forbid other values, because a valid model
    # may, e.g., list NW rows — what matters for context-carry is that the
    # narrowed NW count (300) is present in the table OR the prose answer.
    nw_true = TRUE_REGION_COUNTS["NW"]  # 300

    def _result_table_numbers(table):
        nums = set()
        for row in table:
            for v in row.values():
                try:
                    nums.add(int(round(float(v))))
                except (TypeError, ValueError):
                    pass
        return nums

    table_nums = _result_table_numbers(data2["result_table"] or [])
    answer_nums = {
        int(n.replace(",", ""))
        for n in re.findall(r"\d[\d,]*", data2["answer"])
    }
    assert nw_true in (table_nums | answer_nums), (
        f"follow-up did not reflect the narrowed NW count {nw_true} in "
        f"result_table {data2['result_table']} or answer "
        f"{data2['answer']!r} — context did not carry"
    )

    # Two turns persisted in this conversation.
    with Session(_isolated_db) as s:
        turns = (
            s.query(Turn).filter(Turn.conversation_id == conversation_id).all()
        )
        assert len(turns) == 2
