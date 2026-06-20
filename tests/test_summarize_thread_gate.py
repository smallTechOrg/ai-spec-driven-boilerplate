"""P3 stub capability gate — bound by the [@eval] token in spec/capabilities/summarize-thread.md.

Asserts the STUB CONTRACT (a fixed, well-formed summary record), not real summarization behaviour.
"""
import json

from agent.runner import run_agent
from tests.helpers import SingleToolFakeModel


async def test_summary_returns_open_question():
    thread = "Customer: my order is late.\n\nAgent: tracking?\n\nCustomer: TRK123, still nothing."
    model = SingleToolFakeModel("summarize_thread", {"thread": thread})
    out = await run_agent("summarize this thread", model=model, run_id="sum-1")
    record = json.loads(out["answer"])
    assert record["open_question"]                  # states the open question
    assert isinstance(record["messages_seen"], int)  # reports a count of messages seen
    assert record["messages_seen"] >= 1
