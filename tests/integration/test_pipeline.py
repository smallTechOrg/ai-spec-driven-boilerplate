"""Integration tests — require real LLM key (Anthropic or Gemini)."""
import pytest
from sqlalchemy.orm import Session

from graph.runner import run_agent
from db import session as session_module
from db.models import RunRow


@pytest.mark.usefixtures("_require_llm_key")
def test_pipeline_runs_end_to_end(_isolated_db):
    run_id = run_agent("Explain why the sky is blue in one sentence.")
    assert run_id is not None
    with Session(session_module._engine) as s:
        run = s.get(RunRow, run_id)
    assert run is not None
    assert run.status == "completed"
    assert run.output_text and len(run.output_text) > 10
    assert run.error_message is None


@pytest.mark.usefixtures("_require_llm_key")
def test_pipeline_stores_input(_isolated_db):
    input_text = "The quick brown fox."
    run_id = run_agent(input_text)
    with Session(session_module._engine) as s:
        run = s.get(RunRow, run_id)
    assert run.input_text == input_text


@pytest.mark.usefixtures("_require_llm_key")
def test_pipeline_via_api(api_client):
    """Full HTTP round-trip: POST /runs -> 200 with output_text."""
    r = api_client.post("/runs", json={"input_text": "Say hello in three words."})
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["status"] == "completed"
    assert body["data"]["output_text"]
    assert not body["data"].get("error")


@pytest.mark.usefixtures("_require_llm_key")
def test_pipeline_error_surfaces_in_api(api_client):
    """Error must appear in response body, never silently swallowed."""
    r = api_client.post("/runs", json={"input_text": "x"})
    assert r.status_code == 200
    body = r.json()
    # Either output or error must be set
    assert body["data"]["output_text"] or body["data"].get("error")
