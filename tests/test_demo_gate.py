"""The in-process twin of gate check 6 — a REAL run_agent + a REAL stable_outcome_eval judge. With a funded
key it runs as the gate's check-6 mirror; keyless it is cleanly SKIPPED (run_agent would raise without a key)."""
import os

import pytest

from agent.evals import stable_outcome_eval, trajectory_eval
from agent.runner import run_agent


@pytest.mark.skipif(not os.getenv("APP_LLM_API_KEY"), reason="real run + LLM judge needs a funded key")
async def test_demo_gate():
    run_id = "gate-1"
    GOAL = ("Please triage this support ticket and draft a reply: 'I was charged twice for my subscription "
            "this month and I'm really frustrated. When will I get my money back?'")
    state = await run_agent(GOAL, run_id=run_id)              # real run, real model
    ok_o, mean, detail = await stable_outcome_eval(           # multi-sample judge — deterministic, not a coin-flip
        goal=GOAL, answer=state["answer"],
        criterion=("WHEN a support ticket is submitted the system SHALL classify it with an urgency label "
                   "and a category label and draft a suggested reply to the customer."),
        evaluation_steps=[
            "Does the answer assign an urgency label (one of low/normal/high/urgent)?",
            "Does the answer assign a category label (one of billing/technical/account/shipping/general)?",
            "Does the answer include a drafted reply addressed to the customer that states a next step?",
            "Is the drafted reply free of invented policies or contradictory timeframes?",
        ])
    ok_t, reasons = await trajectory_eval(run_id, expect_tools=["classify_ticket"], forbid_tools=[])
    assert ok_o, f"OUTCOME failed: judge mean {mean} {detail}"   # a 200 with a wrong answer FAILS here
    # 1-capability slice: trajectory is advisory — log it, don't block. Promote to `assert ok_t` at capability #2.
    if not ok_t:
        print(f"TRAJECTORY advisory (not blocking until a 2nd capability): {reasons}")
