# Agent Graph — BlogForge

## State Type

```python
from typing import TypedDict
from blogforge.domain.models import Blog, Writer, Post

class GenerationState(TypedDict):
    run_id: int
    blog: Blog
    posts_count: int                        # how many posts to generate this run
    topics: list[str]                       # filled by node_topic_discovery
    assignments: list[tuple[str, Writer]]   # (topic, writer) pairs; filled by node_writer_assignment
    completed_posts: list[Post]             # filled incrementally by node_post_generation
    failed_topics: list[str]               # topics that failed post generation
    error: str | None                       # set by any node on fatal error
```

## Nodes

| Node | Responsibility |
|------|---------------|
| `node_topic_discovery` | DuckDuckGo + Tavily parallel search → Gemini selection → dedup vs UsedTopic |
| `node_writer_assignment` | Round-robin assignment of writers to topics |
| `node_post_generation` | For each (topic, writer) pair: call Gemini, save post to DB, add UsedTopic |
| `node_image_generation` | For each completed post: call Gemini Imagen, save image, update post record |
| `node_handle_error` | Log the fatal error, update run status to "failed" in DB |
| `node_finalize` | Update run status to "completed", log summary |

## Edge Topology

```
START
  │
  ▼
node_topic_discovery ──[error]──► node_handle_error ──► END
  │
  ▼
node_writer_assignment ──[error]──► node_handle_error ──► END
  │
  ▼
node_post_generation   (partial failures allowed — no fatal routing)
  │
  ▼
node_image_generation  (partial failures allowed — SVG fallback)
  │
  ▼
node_finalize ──► END
```

Conditional routing: after `node_topic_discovery` and `node_writer_assignment`, if `state["error"]` is set, route to `node_handle_error`; otherwise continue to next node.

## Error Handler

`node_handle_error` receives state with `error` set. It:
1. Logs the error at ERROR level
2. Updates the Run record in DB to status="failed", error_message=state["error"]
3. Returns state unchanged (graph ends at END after this node)

## Finalize

`node_finalize`:
1. Updates Run record to status="completed"
2. Logs a summary: topics discovered, posts written, posts failed, images generated
3. Returns state unchanged

## Graph Assembly

```python
from langgraph.graph import StateGraph, END
from blogforge.agent.state import GenerationState
from blogforge.agent.nodes import (
    node_topic_discovery,
    node_writer_assignment,
    node_post_generation,
    node_image_generation,
    node_handle_error,
    node_finalize,
)

def _route_after_discovery(state: GenerationState) -> str:
    return "node_handle_error" if state.get("error") else "node_writer_assignment"

def _route_after_assignment(state: GenerationState) -> str:
    return "node_handle_error" if state.get("error") else "node_post_generation"

def build_graph() -> StateGraph:
    g = StateGraph(GenerationState)
    g.add_node("node_topic_discovery", node_topic_discovery)
    g.add_node("node_writer_assignment", node_writer_assignment)
    g.add_node("node_post_generation", node_post_generation)
    g.add_node("node_image_generation", node_image_generation)
    g.add_node("node_handle_error", node_handle_error)
    g.add_node("node_finalize", node_finalize)

    g.set_entry_point("node_topic_discovery")
    g.add_conditional_edges("node_topic_discovery", _route_after_discovery)
    g.add_conditional_edges("node_writer_assignment", _route_after_assignment)
    g.add_edge("node_post_generation", "node_image_generation")
    g.add_edge("node_image_generation", "node_finalize")
    g.add_edge("node_finalize", END)
    g.add_edge("node_handle_error", END)
    return g

graph = build_graph().compile()
```

## Concurrency Model

- `node_topic_discovery`: DuckDuckGo and Tavily called concurrently via `asyncio.gather`
- `node_post_generation`: posts generated sequentially (Gemini rate limit safety); DB writes after each post
- `node_image_generation`: images generated sequentially; SVG fallback if Imagen fails
- The entire graph runs inside a single `asyncio` event loop (no threading)
