"""Integration tests for Phase 4: Data Quality Inspection + Auto-Clean."""

import json
import os
import tempfile
import pytest


def _upload_csv(api_client, session_id, csv_content, filename="test.csv"):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(csv_content)
        tmp_path = f.name
    try:
        with open(tmp_path, "rb") as fh:
            r = api_client.post(
                f"/sessions/{session_id}/files",
                files={"file": (filename, fh, "text/csv")},
            )
        assert r.status_code == 200, f"Upload failed: {r.text}"
        return r.json()["data"]
    finally:
        os.unlink(tmp_path)


def _ask(api_client, session_id, question="What is the average value?"):
    r = api_client.post(
        f"/sessions/{session_id}/messages",
        json={"content": question},
    )
    assert r.status_code == 200, f"Message failed: {r.text}"
    return r.json()["data"]


class TestNoIssuesCleanData:
    def test_no_issues_on_clean_csv(self, api_client, _require_llm_key):
        csv = (
            "name,value,count\n"
            "alice,10.5,3\n"
            "bob,20.0,5\n"
            "carol,15.25,7\n"
            "dave,8.75,2\n"
            "eve,12.0,4\n"
        )
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        _upload_csv(api_client, sid, csv, "clean.csv")
        resp = _ask(api_client, sid, "What is the average value?")
        qr = resp.get("quality_report")
        assert qr is not None, "quality_report key must be returned in response"
        assert qr["has_issues"] is False
        assert qr["clean_actions"] == []


class TestDuplicateRemoval:
    def test_duplicate_rows_detected_and_removed(self, api_client, _require_llm_key):
        csv = (
            "name,value\n"
            "alice,10\n"
            "bob,20\n"
            "alice,10\n"
            "carol,30\n"
            "alice,10\n"
        )
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        _upload_csv(api_client, sid, csv, "dups.csv")
        resp = _ask(api_client, sid, "How many rows are there?")
        qr = resp.get("quality_report")
        assert qr is not None, "quality_report should be present"
        assert qr["has_issues"] is True
        actions_text = " ".join(qr["clean_actions"]).lower()
        assert "duplicate" in actions_text or "removed" in actions_text, (
            f"Expected duplicate removal message, got: {qr['clean_actions']}"
        )
        assert len(qr["files"]) > 0
        assert qr["files"][0]["duplicate_rows_removed"] > 0


class TestNumericStringCoercion:
    def test_numeric_string_column_coercion_handled_gracefully(
        self, api_client, _require_llm_key
    ):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write("product,price,qty\n")
            for i in range(6):
                f.write('item{},"{}.00",{}\n'.format(i, 10 + i * 5, i + 1))
            tmp_path = f.name
        try:
            sid = api_client.post("/sessions").json()["data"]["session_id"]
            with open(tmp_path, "rb") as fh:
                r = api_client.post(
                    "/sessions/{}/files".format(sid),
                    files={"file": ("prices.csv", fh, "text/csv")},
                )
            assert r.status_code == 200
            resp = _ask(api_client, sid, "What is the total price?")
            qr = resp.get("quality_report")
            assert qr is not None
            assert isinstance(qr["has_issues"], bool)
            assert isinstance(qr["clean_actions"], list)
            assert isinstance(qr["files"], list)
        finally:
            os.unlink(tmp_path)


class TestInvalidDatesReported:
    def test_invalid_dates_in_date_column_reported(self, api_client, _require_llm_key):
        csv = (
            "order_date,revenue\n"
            "2024-01-15,100\n"
            "2024-02-10,200\n"
            "not-a-date,300\n"
            "2024-04-01,400\n"
            "2024-05-15,500\n"
        )
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        _upload_csv(api_client, sid, csv, "orders.csv")
        resp = _ask(api_client, sid, "What is the total revenue?")
        qr = resp.get("quality_report")
        assert qr is not None
        all_issues = [
            issue
            for fr in qr.get("files", [])
            for issue in fr.get("issues", [])
        ]
        date_issues = [i for i in all_issues if i.get("category") == "invalid_dates"]
        assert len(date_issues) > 0, (
            "Expected invalid_dates issue but got: {}".format(all_issues)
        )
        assert not any(
            "order_date" in a and "coerced" in a.lower()
            for a in qr["clean_actions"]
        )


class TestOutliersReported:
    def test_outliers_detected_not_removed(self, api_client, _require_llm_key):
        rows = ["value,category"]
        for i in range(15):
            rows.append("{},cat".format(10 + i * 0.5))
        rows.append("99999.0,cat")
        csv = "\n".join(rows) + "\n"

        sid = api_client.post("/sessions").json()["data"]["session_id"]
        _upload_csv(api_client, sid, csv, "outliers.csv")
        resp = _ask(api_client, sid, "What is the average value?")
        qr = resp.get("quality_report")
        assert qr is not None
        all_issues = [
            issue
            for fr in qr.get("files", [])
            for issue in fr.get("issues", [])
        ]
        outlier_issues = [i for i in all_issues if i.get("category") == "outliers"]
        assert len(outlier_issues) > 0, (
            "Expected outlier issue but got: {}".format(all_issues)
        )
        assert not any("outlier" in a.lower() for a in qr["clean_actions"])


class TestPrivacy:
    def test_quality_report_contains_no_raw_row_values(
        self, api_client, _require_llm_key
    ):
        csv = (
            "name,secret_value,amount\n"
            "alice_secret_xyz,PRIVATE_DATA_123,100\n"
            "bob_secret_abc,CONFIDENTIAL_456,200\n"
            "carol_secret_def,SENSITIVE_789,300\n"
            "dave_extra_row,EXTRA_DATA_000,400\n"
            "dave_extra_row,EXTRA_DATA_000,400\n"
        )
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        _upload_csv(api_client, sid, csv, "private.csv")
        resp = _ask(api_client, sid, "What is the sum of amount?")
        qr = resp.get("quality_report")
        assert qr is not None
        qr_str = json.dumps(qr)
        forbidden = [
            "alice_secret_xyz",
            "PRIVATE_DATA_123",
            "CONFIDENTIAL_456",
            "SENSITIVE_789",
            "EXTRA_DATA_000",
            "bob_secret_abc",
            "carol_secret_def",
        ]
        for val in forbidden:
            assert val not in qr_str, (
                "Raw cell value '{}' found in quality_report -- privacy violation!".format(val)
            )
