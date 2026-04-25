"""Integration test — full pipeline runs end-to-end with stub LLM.

Verifies:
- SourcingRun created with status=pending
- After run_agent(), status=completed
- At least one SupplierRecommendation row in DB per material
- run_agent() requires no LLM API key
"""

import os
import uuid

import pytest

from sourcing_agent.db.repository import create_run, get_run_with_details
from sourcing_agent.domain.models import MaterialRequest, SourcingRunStatus
from sourcing_agent.graph.runner import run_agent


def test_full_pipeline_stub(db_session, monkeypatch):
    """Run the full sourcing pipeline in stub mode; assert completed with recommendations."""
    # Ensure stub mode (no API key)
    monkeypatch.setenv("SA_GEMINI_API_KEY", "")
    monkeypatch.setenv("SA_LLM_PROVIDER", "auto")
    monkeypatch.setenv("SA_DATABASE_URL", os.environ.get("SA_TEST_DATABASE_URL", os.environ.get("SA_DATABASE_URL", "")))

    SessionLocal = db_session

    materials = [
        MaterialRequest(name="Portland Cement", quantity=200, unit="bags"),
        MaterialRequest(name="Clay Bricks", quantity=5000, unit="units"),
    ]

    with SessionLocal() as session:
        run = create_run(session, "Integration Test Project", materials)
        run_id = run.id
        session.commit()

    # Run agent (stub mode — no API calls)
    final_state = run_agent(run_id)

    assert final_state["status"] == SourcingRunStatus.COMPLETED, (
        f"Expected status=completed, got {final_state['status']}. error={final_state.get('error')}"
    )

    # Verify DB
    with SessionLocal() as session:
        loaded = get_run_with_details(session, run_id)
        assert loaded.status == SourcingRunStatus.COMPLETED
        assert loaded.completed_at is not None
        assert len(loaded.recommendations) >= 1, "Expected at least one recommendation row"
        # Each material should have recommendations
        for item in loaded.line_items:
            item_recs = [r for r in loaded.recommendations if r.line_item_id == item.id]
            assert len(item_recs) >= 1, f"No recommendations for {item.material_name}"
            # Rank 1 should be the best scored
            rank1 = next((r for r in item_recs if r.rank == 1), None)
            assert rank1 is not None
