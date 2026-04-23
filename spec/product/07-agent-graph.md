# Agent Graph

## State

```python
class AgentState(TypedDict):
    run_id: str              # AgentRun.id
    writer_id: str
    voice_id: str
    topic: str
    notes: str | None

    persona: str             # loaded from writer
    guidelines: str          # loaded from voice

    outline: str | None      # set by node_plan
    draft: str | None        # set by node_draft
    title: str | None        # set by node_finalize
    body: str | None         # set by node_finalize

    article_id: str | None   # set after persistence
    error: str | None
```

## Nodes

### `node_plan`
**Reads:** topic, notes, persona, guidelines
**Writes:** outline
**External:** Gemini `generate(prompt="... outline ...")`. On failure → set `error`.
**Behaviour:** Asks the LLM for a 3–6 bullet outline consistent with voice+persona.

### `node_draft`
**Reads:** outline, persona, guidelines, topic
**Writes:** draft
**External:** Gemini `generate(prompt="... draft ...")`. On failure → set `error`.
**Behaviour:** Expands the outline into a full markdown draft.

### `node_finalize`
**Reads:** draft, topic
**Writes:** title, body, article_id
**External:** Gemini `generate(prompt="... title + polish ...")`; Postgres insert Article.
**Behaviour:** Produces a short title, light polish, inserts Article row, marks AgentRun `completed`.

### `node_handle_error`
**Reads:** error, run_id
**Writes:** (DB) AgentRun.status=`failed`, error_message.
**Behaviour:** Terminates gracefully.

## Edge Topology

```
START → node_plan ──(error)──► node_handle_error ──► END
          │
          ▼
        node_draft ──(error)──► node_handle_error
          │
          ▼
        node_finalize ──(error)──► node_handle_error
          │
          ▼
         END
```

## Graph Assembly

```python
graph = StateGraph(AgentState)
graph.add_node("plan", node_plan)
graph.add_node("draft", node_draft)
graph.add_node("finalize", node_finalize)
graph.add_node("handle_error", node_handle_error)
graph.set_entry_point("plan")

def _route(s):
    return "handle_error" if s.get("error") else "__next__"

graph.add_conditional_edges("plan", lambda s: "handle_error" if s.get("error") else "draft")
graph.add_conditional_edges("draft", lambda s: "handle_error" if s.get("error") else "finalize")
graph.add_conditional_edges("finalize", lambda s: "handle_error" if s.get("error") else END)
graph.add_edge("handle_error", END)
compiled_graph = graph.compile()
```

## Concurrency Model

- One run at a time per HTTP request; no cross-request locking in v0.1.
- No checkpointing for v0.1.
