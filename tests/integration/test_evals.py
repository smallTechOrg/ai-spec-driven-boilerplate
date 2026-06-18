"""Eval skeleton test — runs the fixed eval set against the real model, loose asserts."""

from __future__ import annotations

import os

import pytest

from evals.harness import run_evals

pytestmark = pytest.mark.skipif(
    not (os.environ.get("DATA_ANALYST_GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
    reason="Real Gemini key not set.",
)


@pytest.mark.asyncio
async def test_eval_suite_mostly_passes(db_session):
    results = await run_evals(db_session)
    assert len(results) >= 3
    passed = sum(1 for r in results if r.passed)
    # Loose gate: the agent gets the majority of representative questions right.
    assert passed >= 2, f"only {passed}/{len(results)} eval cases passed"
