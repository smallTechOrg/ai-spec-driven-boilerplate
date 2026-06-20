"""Long-term (cross-session) memory — keyless tests of the durable store + the remember tool."""
from agent.memory import recall, recall_text, remember


async def test_long_term_memory_persists():
    """A remembered fact is durably stored and recalled later (any session sees it)."""
    await remember("The user prefers concise answers.")
    facts = await recall()
    assert any("concise" in f for f in facts)
    assert "concise" in await recall_text()


async def test_long_term_memory_via_tool():
    """The remember tool writes a durable fact through the agent's tool interface."""
    from agent.tools import remember as remember_tool
    await remember_tool.ainvoke({"fact": "The user is based in Mumbai."})
    assert any("Mumbai" in f for f in await recall())
