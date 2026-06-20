"""P2 stub capability gate — bound by the [@eval] token in spec/capabilities/escalate-ticket.md.

Asserts the STUB CONTRACT (a fixed, well-formed escalation record), not real routing behaviour.
"""
import json

from agent.runner import run_agent
from tests.helpers import SingleToolFakeModel


async def test_escalation_returns_queue_record():
    model = SingleToolFakeModel("escalate_ticket", {"reason": "urgent billing dispute", "queue": "tier-2"})
    out = await run_agent("escalate this ticket", model=model, run_id="esc-1")
    # the finish answer echoes the escalation record the stub tool returned
    record = json.loads(out["answer"])
    assert record["queue"] == "tier-2"          # names the target queue
    assert record["status"] == "escalated"      # status is escalated
    assert record["reason"] == "urgent billing dispute"
