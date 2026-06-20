"""Shared test helpers — import absolutely: `from tests.helpers import ...` (tests/ is a package)."""
import json

from langchain_core.messages import AIMessage, ToolMessage


class FakeModel:
    """Scripted fake model (no API key). Returns the i-th message each call; clamps at the last one."""

    def __init__(self, scripted):
        self.s = list(scripted)
        self.i = 0

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, msgs):
        m = self.s[min(self.i, len(self.s) - 1)]
        self.i += 1
        return m


class TriageFakeModel:
    """Context-aware fake model (no API key) that drives the REAL triage pipeline: it calls classify_ticket,
    then search_policy on the returned category, then finishes with an answer composed from the REAL tool
    outputs — so a grounding bug surfaces in the assertions (observability-and-evals.md § ContextAwareFakeModel).

    `refuse=True` makes the finish answer decline an irreversible action (drives test_refuses_irreversible_action)."""

    def __init__(self, ticket_text: str, refuse: bool = False):
        self.ticket_text = ticket_text
        self.refuse = refuse
        self._classified = None   # holds the JSON from classify_ticket once it has run

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, msgs):
        last = msgs[-1]
        if isinstance(last, ToolMessage):
            content = str(last.content)
            # Is this the classify result? (JSON with urgency/category) -> next call search_policy.
            try:
                parsed = json.loads(content)
            except (ValueError, TypeError):
                parsed = None
            if isinstance(parsed, dict) and "urgency" in parsed and "category" in parsed:
                self._classified = parsed
                return AIMessage(content="", tool_calls=[
                    {"name": "search_policy", "args": {"category": parsed["category"]}, "id": "p"}])
            # Otherwise this is the policy result -> compose the final answer from the REAL tool outputs.
            c = self._classified or {"urgency": "normal", "category": "general"}
            policy = content
            if self.refuse:
                reply = ("Dear customer, thank you for reaching out. I'm sorry for the trouble. I'm not able "
                         "to issue a refund myself — an authorized human agent must handle that. I've flagged "
                         "your request so the team can review it. " + policy)
            else:
                reply = ("Dear customer, thank you for contacting support. I understand the issue and we're "
                         "on it. Next step: " + policy)
            answer = f"Urgency: {c['urgency']}\nCategory: {c['category']}\n\nReply:\n{reply}"
            return AIMessage(content="", tool_calls=[
                {"name": "finish", "args": {"answer": answer}, "id": "f"}])
        # First call: classify the ticket.
        return AIMessage(content="", tool_calls=[
            {"name": "classify_ticket", "args": {"ticket_text": self.ticket_text}, "id": "c"}])


class SingleToolFakeModel:
    """Fake model that calls ONE named tool with given args, then finishes echoing its output. Used for the
    P2/P3 stub gate tests (escalate_ticket, summarize_thread)."""

    def __init__(self, tool_name: str, args: dict):
        self.tool_name = tool_name
        self.args = args

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, msgs):
        last = msgs[-1]
        if isinstance(last, ToolMessage):
            return AIMessage(content="", tool_calls=[
                {"name": "finish", "args": {"answer": str(last.content)}, "id": "f"}])
        return AIMessage(content="", tool_calls=[
            {"name": self.tool_name, "args": self.args, "id": "t"}])
