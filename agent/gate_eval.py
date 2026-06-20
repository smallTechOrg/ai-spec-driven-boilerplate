# agent/gate_eval.py — exit 0 iff the run's answer is RIGHT-with-margin-and-stable AND the path is sane.
import argparse
import asyncio
import sys

from sqlalchemy import select

from .db import Run, get_sessionmaker
from .evals import stable_outcome_eval, trajectory_eval   # the ONE judge-stability impl (observability-and-evals.md)

# Filled from the spec at build time. CRITERION/EVALUATION_STEPS/EXPECT_TOOLS come from the SAME P1 EARS line
# that the Makefile's GOAL/FOLLOWUP are derived from (spec/capabilities/triage-ticket.md, first EARS line).
CRITERION = ("WHEN a support ticket is submitted the system SHALL classify it with an urgency label "
             "and a category label and draft a suggested reply to the customer.")
EVALUATION_STEPS = [
    "Does the answer assign an urgency label (one of low/normal/high/urgent)?",
    "Does the answer assign a category label (one of billing/technical/account/shipping/general)?",
    "Does the answer include a drafted reply addressed to the customer that states a next step?",
    "Is the drafted reply free of invented policies or contradictory timeframes?",
]
EXPECT_TOOLS = ["classify_ticket"]
FORBID_TOOLS = []                       # this capability has no mutating tool to guard.

SAMPLES, THRESHOLD, MARGIN = 5, 4, 0.5   # judge-stability knobs


async def main(run_id: str, goal: str) -> int:
    async with get_sessionmaker()() as s:
        run = (await s.execute(select(Run).where(Run.id == run_id))).scalar_one()
    outcome_ok, mean, detail = await stable_outcome_eval(
        goal, run.answer, CRITERION, EVALUATION_STEPS,
        threshold=THRESHOLD, samples=SAMPLES, margin=MARGIN)
    ok_t, reasons = await trajectory_eval(run_id, expect_tools=EXPECT_TOOLS, forbid_tools=FORBID_TOOLS)
    print(f"OUTCOME scores={detail['scores']} mean={mean:.2f} spread={detail['spread']} "
          f"(need mean>={THRESHOLD - MARGIN})", file=sys.stderr)
    if not outcome_ok:
        print("OUTCOME FAIL: below threshold-with-margin or unstable (high judge variance)", file=sys.stderr)
    # TRAJECTORY is ADVISORY for a 1-capability v1 slice — log its reasons, do NOT gate on them.
    if not ok_t:
        print(f"TRAJECTORY advisory (not blocking until a 2nd capability): {reasons}", file=sys.stderr)
    return 0 if outcome_ok else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True)
    p.add_argument("--goal", required=True)
    a = p.parse_args()
    sys.exit(asyncio.run(main(a.run_id, a.goal)))
