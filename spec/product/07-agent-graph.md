# Agent Graph — Email Triage

## State Type
```python
class TriageState(TypedDict):
    run_id: int
    emails: list[Email]           # filled by fetch_emails
    results: list[EmailResult]    # filled incrementally by classify_and_draft
    error: str | None
```

## Nodes
| Node | Reads | Writes | External calls |
|------|-------|--------|---------------|
| fetch_emails | run_id | emails | Gmail API |
| classify_and_draft | emails | results | Claude API (per email) |
| persist_results | results | — | SQLite |
| handle_error | error | — | SQLite (update run) |
| finalize | results | — | SQLite (update run) |

## Edge Topology
```
START → fetch_emails
fetch_emails →[error]→ handle_error → END
fetch_emails →[ok]→ classify_and_draft → persist_results → finalize → END
```

## Graph Assembly
```python
g = StateGraph(TriageState)
g.add_node("fetch_emails", fetch_emails)
g.add_node("classify_and_draft", classify_and_draft)
g.add_node("persist_results", persist_results)
g.add_node("handle_error", handle_error)
g.add_node("finalize", finalize)
g.set_entry_point("fetch_emails")
g.add_conditional_edges("fetch_emails",
    lambda s: "handle_error" if s.get("error") else "classify_and_draft")
g.add_edge("classify_and_draft", "persist_results")
g.add_edge("persist_results", "finalize")
g.add_edge("finalize", END)
g.add_edge("handle_error", END)
graph = g.compile()
```

## Concurrency Model
classify_and_draft processes emails sequentially (API rate limit safety).
