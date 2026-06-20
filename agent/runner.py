import uuid

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy import select

from .config import get_settings
from .db import Message, Run, Span, get_sessionmaker
from .graph import build_graph
from .llm import get_model
from .observability import span

DOMAIN_PROMPT = (
    "You are a customer-support triage assistant. For an incoming ticket you: "
    "(1) classify its URGENCY as one of low, normal, high, urgent, and its CATEGORY as one of "
    "billing, technical, account, shipping, general; (2) draft a short, professional SUGGESTED REPLY "
    "to the customer that acknowledges their problem and states the concrete next step.\n\n"
    "Rules:\n"
    "- ALWAYS call the classify_ticket tool to obtain the urgency and category — never guess them.\n"
    "- Call search_policy for the relevant category BEFORE stating any timeframe or procedure in the "
    "reply, and ground the reply in what it returns — never invent a policy or a number.\n"
    "- If the ticket demands an irreversible action (issue a refund, delete an account, charge a card), "
    "DO NOT perform it: state in the reply that it must be handled by an authorized human.\n"
    "- Keep the reply concise, empathetic, and free of internal jargon.\n"
    "- Present the final answer as: the Urgency, then the Category, then the drafted Reply.\n"
    "Call finish exactly once with that final answer."
)


async def run_agent(goal: str, model=None, run_id: str | None = None,
                    session_id: str | None = None, checkpointer=None) -> dict:
    settings = get_settings()
    run_id = run_id or uuid.uuid4().hex
    model = model or get_model()

    async with get_sessionmaker()() as s:
        s.add(Run(id=run_id, goal=goal, status="running", iterations=0, thread_id=session_id))
        await s.commit()

    graph = build_graph(model, checkpointer=checkpointer)   # ONE compile; saver = short-term memory
    config = {"recursion_limit": 50}
    # SHORT-TERM MEMORY: with a checkpointer + a session_id, reload this thread's transcript and compose the
    # seed as prior(stale SystemMessage stripped) + fresh SystemMessage + new goal. No add_messages reducer,
    # so the runner — not the channel — owns the merge.
    prior: list = []
    if checkpointer is not None and session_id:
        config["configurable"] = {"thread_id": session_id}
        cp = await checkpointer.aget(config)                 # raw checkpoint dict, or None on turn 1
        if cp:
            saved = cp["channel_values"].get("messages", [])
            prior = [m for m in saved if not isinstance(m, SystemMessage)]   # drop the stale system prompt
    state = {
        "messages": prior + [SystemMessage(content=DOMAIN_PROMPT), HumanMessage(content=goal)],
        "iterations": 0, "answer": None, "run_id": run_id,
    }
    # SESSION CONTEXT FOR TOOLS: guarded import — this agent ships no sessions.py (no data-ingest), so this
    # falls through to None and the run is single-resource. Kept verbatim so the runner stays portable.
    try:
        from .sessions import current_session_id      # generated for data agents (C-SESSION-SCOPE) only
    except ImportError:
        current_session_id = None
    token = current_session_id.set(session_id) if current_session_id is not None else None
    try:
        async with span(run_id, "invoke_agent", "INTERNAL", goal=goal):
            result = await graph.ainvoke(state, config=config)
    finally:
        if token is not None:
            current_session_id.reset(token)

    async with get_sessionmaker()() as s:
        for m in result["messages"]:
            role = "assistant" if isinstance(m, AIMessage) else getattr(m, "type", "system")
            content = m.content if isinstance(m.content, str) else str(m.content)
            s.add(Message(id=uuid.uuid4().hex, run_id=run_id, role=role, content=content))
        # sum this run's LLM-span tokens into first-class cost columns (the /traces dashboard reads these)
        spans = (await s.execute(select(Span).where(Span.run_id == run_id, Span.kind == "LLM"))).scalars().all()
        tok_in = sum((sp.attributes or {}).get("tokens", {}).get("input", 0) for sp in spans)
        tok_out = sum((sp.attributes or {}).get("tokens", {}).get("output", 0) for sp in spans)
        run = (await s.execute(select(Run).where(Run.id == run_id))).scalar_one()
        run.status, run.answer, run.iterations = "completed", result["answer"], result["iterations"]
        run.input_tokens, run.output_tokens = tok_in, tok_out
        run.cost_usd = (tok_in * settings.price_in + tok_out * settings.price_out) / 1_000_000
        await s.commit()

    return {"run_id": run_id, "thread_id": session_id, "status": "completed",
            "answer": result["answer"], "iterations": result["iterations"],
            "messages": result["messages"]}
