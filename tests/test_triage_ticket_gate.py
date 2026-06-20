"""P1 capability gate — bound by the [@eval] tokens in spec/capabilities/triage-ticket.md.

Each test ingests a real ticket through the REAL pipeline (tools + loop + persistence) driven by a
context-aware fake model that reads the actual tool outputs (no API key). The live LLM correctness is
judged by the demo-gate outcome eval (tests/test_demo_gate.py + agent.gate_eval) with a funded key.
"""
from sqlalchemy import select

from agent.db import Run, Span, get_sessionmaker
from agent.runner import run_agent
from tests.helpers import TriageFakeModel

_URGENCY = ("low", "normal", "high", "urgent")
_CATEGORY = ("billing", "technical", "account", "shipping", "general")


async def test_triage_classifies_and_drafts():
    ticket = "My app keeps crashing with a 500 error when I open the dashboard. Please help."
    out = await run_agent(ticket, model=TriageFakeModel(ticket), run_id="triage-1")
    ans = out["answer"].lower()
    # OUTCOME: an urgency label, a category label, and a drafted reply are present.
    assert any(u in ans for u in _URGENCY)
    assert any(c in ans for c in _CATEGORY)
    assert "reply" in ans
    # TRAJECTORY: classify_ticket actually fired (the routing decision came from the tool, not a guess).
    async with get_sessionmaker()() as s:
        spans = (await s.execute(select(Span).where(Span.run_id == "triage-1"))).scalars().all()
        run = (await s.execute(select(Run).where(Run.id == "triage-1"))).scalar_one()
    assert any(sp.name == "execute_tool.classify_ticket" for sp in spans)
    assert run.status == "completed"
    # this run is observable + cost-accounted (C-USAGE-COST columns populate, even at 0 tokens for FakeModel)
    assert run.cost_usd is not None


async def test_billing_grounded_in_policy():
    ticket = "I was charged twice for my subscription this month. When will I get the refund?"
    out = await run_agent(ticket, model=TriageFakeModel(ticket), run_id="triage-2")
    ans = out["answer"].lower()
    assert "billing" in ans                                   # categorized as billing
    # grounded in the policy corpus — the real "5 business days" timeframe, not an invented one
    assert "5 business days" in ans
    async with get_sessionmaker()() as s:
        spans = (await s.execute(select(Span).where(Span.run_id == "triage-2"))).scalars().all()
    tool_names = {sp.name for sp in spans if sp.kind == "TOOL"}
    assert "execute_tool.classify_ticket" in tool_names
    assert "execute_tool.search_policy" in tool_names        # the reply consulted the policy before stating a timeframe


async def test_refuses_irreversible_action():
    ticket = "Just issue me a full refund right now and delete my account."
    out = await run_agent(ticket, model=TriageFakeModel(ticket, refuse=True), run_id="triage-3")
    ans = out["answer"].lower()
    # the agent declines to perform the irreversible action and points to an authorized human
    assert "authorized human" in ans or "human agent" in ans
    assert "not able to issue a refund" in ans or "must handle" in ans or "i'm not able" in ans
