from langchain_core.messages import ToolMessage
from langgraph.graph import END, START, StateGraph

from .config import get_settings
from .observability import span          # patterns/observability-and-evals.md
from .state import AgentState            # TypedDict: messages, iterations, answer, run_id
from .tools import FINISH, TOOL_MAP, TOOLS   # patterns/tools-and-mcp.md


def build_graph(model, checkpointer=None):
    # checkpointer is OPTIONAL: pass an AsyncSqliteSaver to turn on short-term (multi-turn) memory; leave
    # None for a single-shot run. build_graph owns the ONE .compile() — never compile its return value again.
    bound = model.bind_tools(TOOLS)
    settings = get_settings()

    async def agent_node(state):
        async with span(state["run_id"], f"chat {settings.llm_model}", "LLM") as sp:
            resp = await bound.ainvoke(state["messages"])
            if (u := getattr(resp, "usage_metadata", None)):
                # usage_metadata may be a TypedDict (dict) or an object — guard both
                sp["tokens"] = {
                    "input":  u.get("input_tokens", 0) if isinstance(u, dict) else getattr(u, "input_tokens", 0),
                    "output": u.get("output_tokens", 0) if isinstance(u, dict) else getattr(u, "output_tokens", 0),
                }
        return {"messages": state["messages"] + [resp], "iterations": state["iterations"] + 1}

    async def tools_node(state):
        out = []
        for tc in state["messages"][-1].tool_calls:
            if tc["name"] == FINISH:
                continue
            tool = TOOL_MAP.get(tc["name"])
            async with span(state["run_id"], f"execute_tool.{tc['name']}", "TOOL", args=tc["args"]) as sp:
                # GRACEFUL DEGRADATION: a tool failure must NOT crash the loop — record it, hand the model an
                # error ToolMessage, and let it recover (retry, route around, or finish with what it has).
                try:
                    if not tool:
                        result = f"unknown tool: {tc['name']}"
                    elif getattr(tool, "coroutine", None) is not None:
                        result = await tool.ainvoke(tc["args"])   # ASYNC tool (I/O) — await ainvoke
                    else:
                        result = tool.invoke(tc["args"])          # sync tool (pure-compute, no I/O)
                except Exception as exc:
                    result = f"tool '{tc['name']}' failed: {type(exc).__name__}: {exc}"
                    sp["error"] = result                          # surfaced in /traces in red
                sp["result_preview"] = str(result)[:300]
            out.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
        return {"messages": state["messages"] + out}

    async def finalize_node(state):
        msgs = state["messages"]
        answer = None
        # 1. finish tool's answer — scan backwards (hit cap = AIMessage with tool_calls, not finish)
        for m in reversed(msgs):
            for tc in getattr(m, "tool_calls", None) or []:
                if tc["name"] == FINISH and tc["args"].get("answer"):
                    answer = tc["args"]["answer"]
                    break
            if answer:
                break
        # 2. last AIMessage text — coerce structured content (list-of-parts) to str
        if not answer:
            raw = getattr(msgs[-1], "content", None)
            if isinstance(raw, list):
                raw = "\n".join(p["text"] for p in raw if isinstance(p, dict) and p.get("type") == "text") or None
            answer = raw or None
        # 3. last resort: most recent tool result (best-effort answer, never blank)
        if not answer:
            last_tool = next((m for m in reversed(msgs) if isinstance(m, ToolMessage) and m.content), None)
            if last_tool:
                answer = "Ran out of steps — here is what I gathered:\n\n" + str(last_tool.content)
        return {"answer": answer or "(no answer produced)"}

    def route(state):
        if state["iterations"] >= settings.max_iterations:
            return "finalize"                      # force_finalize
        tcs = getattr(state["messages"][-1], "tool_calls", None)
        if tcs:
            return "finalize" if any(t["name"] == FINISH for t in tcs) else "tools"
        return "finalize"

    g = StateGraph(AgentState)
    g.add_node("agent", agent_node)
    g.add_node("tools", tools_node)
    g.add_node("finalize", finalize_node)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", route, {"tools": "tools", "finalize": "finalize"})
    g.add_edge("tools", "agent")
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)   # None = no persistence; a saver = short-term memory
