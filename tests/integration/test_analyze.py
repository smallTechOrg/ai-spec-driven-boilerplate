"""End-to-end integration against the REAL Gemini provider (key from .env).

These tests prove: full-data execution (not sampling), the privacy boundary on a
real call, run-history persistence, and the upload->profile->ask happy path via the
HTTP surface. Skipped only if no key is set."""
import io

import pandas as pd
import pytest

from tests.fixtures.data import write_skewed_orders_csv


@pytest.fixture
def _data_dir(tmp_path, monkeypatch):
    # Point uploads + storage at a temp dir; key/db come from .env + conftest.
    import config.settings as m
    m._settings = None
    monkeypatch.setenv("AGENT_DATA_DIR", str(tmp_path))
    yield tmp_path
    m._settings = None


@pytest.mark.usefixtures("_require_llm_key")
def test_upload_then_full_data_answer_matches_pandas(api_client, _data_dir):
    # Build a skewed >=10k-row CSV where sample != full-data answer.
    csv_path = _data_dir / "orders.csv"
    truth = write_skewed_orders_csv(csv_path, n=12000)

    # Upload + profile (real endpoint).
    with open(csv_path, "rb") as fh:
        up = api_client.post(
            "/api/datasets", files={"file": ("orders.csv", fh, "text/csv")}
        )
    assert up.status_code == 200, up.text
    ds = up.json()
    assert ds["row_count"] == 12000
    assert ds["column_count"] == 2
    names = {c["name"] for c in ds["profile"]["columns"]}
    assert names == {"region", "order_value"}
    assert len(ds["profile"]["sample"]) <= 20      # bounded sample

    # Ask an aggregate question -> real agentic loop -> full-data answer.
    r = api_client.post(
        "/api/analyses",
        json={"dataset_id": ds["id"], "question": "What is the average order_value for each region?"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed", body
    assert body["code"]
    assert body["result"]

    # Normalise the result (dict or list-of-records) to a region -> mean map.
    result = _region_means(body["result"])

    # The result must match a direct pandas computation over ALL rows — proving
    # full-data execution rather than sampling.
    for region, mean in truth["region_means"].items():
        assert region in result, f"missing region {region} in {result}"
        assert abs(result[region] - mean) < 1.0, (region, result[region], mean)


def _region_means(result) -> dict:
    """Coerce the agent's result into {region: mean}, tolerating shape variation."""
    out: dict[str, float] = {}
    if isinstance(result, dict):
        for k, v in result.items():
            out[str(k)] = round(float(v), 2)
    elif isinstance(result, list):
        for row in result:
            region = row.get("region") or row.get("Region")
            mean = next(
                (row[c] for c in row if c not in ("region", "Region")), None
            )
            if region is not None and mean is not None:
                out[str(region)] = round(float(mean), 2)
    return out


@pytest.mark.usefixtures("_require_llm_key")
def test_privacy_boundary_real_call_sends_only_bounded_sample(api_client, _data_dir, monkeypatch):
    """Capture every real LLM prompt; assert none embeds the full row set."""
    csv_path = _data_dir / "orders.csv"
    write_skewed_orders_csv(csv_path, n=12000)

    captured: list[str] = []
    import llm.client as client_mod
    real_call = client_mod.LLMClient.call_model

    def _spy(self, prompt, *, system=None):
        captured.append(prompt)
        return real_call(self, prompt, system=system)

    monkeypatch.setattr(client_mod.LLMClient, "call_model", _spy)

    with open(csv_path, "rb") as fh:
        ds = api_client.post(
            "/api/datasets", files={"file": ("orders.csv", fh, "text/csv")}
        ).json()
    api_client.post(
        "/api/analyses",
        json={"dataset_id": ds["id"], "question": "average order_value by region?"},
    )

    assert captured, "no LLM call was made"
    for prompt in captured:
        # A bounded sample is far smaller than 12000 rows. Sentinel row indices that
        # only exist deep in the dataset must never appear in any prompt.
        assert "11999" not in prompt
        # Embedded sample announces its bounded size.
        if "SAMPLE" in prompt:
            assert "rows only" in prompt


@pytest.mark.usefixtures("_require_llm_key")
def test_run_is_persisted_and_retrievable(api_client, _data_dir):
    csv_path = _data_dir / "orders.csv"
    write_skewed_orders_csv(csv_path, n=12000)
    with open(csv_path, "rb") as fh:
        ds = api_client.post(
            "/api/datasets", files={"file": ("orders.csv", fh, "text/csv")}
        ).json()

    created = api_client.post(
        "/api/analyses",
        json={"dataset_id": ds["id"], "question": "average order_value by region?"},
    ).json()
    analysis_id = created["id"]

    # List endpoint (history, most recent first).
    hist = api_client.get(f"/api/analyses?dataset_id={ds['id']}")
    assert hist.status_code == 200
    rows = hist.json()
    assert any(row["id"] == analysis_id for row in rows)
    row = next(r for r in rows if r["id"] == analysis_id)
    assert row["question"] and row["code"] and row["created_at"]

    # Single full record.
    full = api_client.get(f"/api/analyses/{analysis_id}")
    assert full.status_code == 200
    fr = full.json()
    assert fr["result"] is not None
    assert fr["code"]
    assert fr["created_at"]
