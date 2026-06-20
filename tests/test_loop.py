from langchain_core.messages import AIMessage
from sqlalchemy import select

from agent.db import Run, Span, get_sessionmaker
from agent.runner import run_agent
from tests.helpers import FakeModel


async def test_loop_runs_at_least_two_iterations_with_tool_span():
    # classify_ticket then finish — proves the LOOP runs (≥1 action + finish), not just the nodes (C-LOOP-RUNS).
    scripted = [
        AIMessage(content="", tool_calls=[
            {"name": "classify_ticket", "args": {"ticket_text": "I was charged twice"}, "id": "c"}]),
        AIMessage(content="", tool_calls=[
            {"name": "finish", "args": {"answer": "Urgency: high\nCategory: billing\n\nReply: We're on it."}, "id": "f"}]),
    ]
    out = await run_agent("triage this", model=FakeModel(scripted), run_id="loop-1")
    assert out["iterations"] >= 2
    assert out["answer"]
    async with get_sessionmaker()() as s:
        spans = (await s.execute(select(Span).where(Span.run_id == "loop-1"))).scalars().all()
    tool_spans = [sp for sp in spans if sp.kind == "TOOL"]
    assert any(sp.name == "execute_tool.classify_ticket" for sp in tool_spans)


async def test_force_finalize_never_blank_past_max_iterations():
    # A runaway model that NEVER calls finish must force-finalize a non-blank best-effort answer (C-FINALIZE/C-MAXITER).
    runaway = AIMessage(content="", tool_calls=[
        {"name": "classify_ticket", "args": {"ticket_text": "where is my order"}, "id": "x"}])
    out = await run_agent("triage this", model=FakeModel([runaway]), run_id="loop-2")
    assert out["answer"]                                   # never blank
    assert out["answer"] != "(no answer produced)"        # the fallback chain produced a real best-effort answer


async def test_graceful_degradation_on_tool_failure():
    # An unknown tool name fails soft (recorded as an error ToolMessage) and the run still COMPLETES (C-DEGRADE).
    scripted = [
        AIMessage(content="", tool_calls=[
            {"name": "nonexistent_tool", "args": {"x": 1}, "id": "n"}]),
        AIMessage(content="", tool_calls=[
            {"name": "finish", "args": {"answer": "recovered after a failed tool call"}, "id": "f"}]),
    ]
    out = await run_agent("triage this", model=FakeModel(scripted), run_id="loop-3")
    assert out["answer"]
    async with get_sessionmaker()() as s:
        run = (await s.execute(select(Run).where(Run.id == "loop-3"))).scalar_one()
    assert run.status == "completed"                       # the loop survived the tool failure
