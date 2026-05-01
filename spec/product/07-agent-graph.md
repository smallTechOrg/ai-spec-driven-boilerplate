# Agent Graph

LangGraph `StateGraph` compiled once at import time as `agent_graph`.

## State

`AgentState` (TypedDict, total=False):

| Key | Type | Set by |
|-----|------|--------|
| `run_id` | str | runner |
| `request_id` | str | runner |
| `request` | dict | runner (echo of `SourcingRequest` row) |
| `raw_results` | list[dict] | research node |
| `suppliers` | list[dict] | enrich node |
| `recommendations` | list[dict] | score node |
| `error` | str \| None | any node on failure |

## Nodes

| Node | Reads | Writes | Calls |
|------|-------|--------|-------|
| `research` | `request` | `raw_results` | search provider |
| `enrich` | `raw_results`, `request` | `suppliers` (also persists Supplier rows) | LLM (`<node:enrich>` tag) |
| `score` | `suppliers`, `request` | `recommendations` (also persists Recommendation rows) | LLM (`<node:score>` tag) |
| `handle_error` | `error` | run.status = failed | — |
| `finalize` | `recommendations` | run.status = completed | — |

## Edges

```
START → research
research  --(error?)→ handle_error | enrich
enrich    --(error?)→ handle_error | score
score     --(error?)→ handle_error | finalize
finalize  → END
handle_error → END
```

## Stub branching (offline mode)

Each node injects an unambiguous tag into its prompt. The stub LLM provider
matches on the tag, never on prose:

- `<node:enrich>` → returns supplier dicts shaped like real Gemini output:
  paragraphs of prose enrichment, not bullets.
- `<node:score>` → returns a JSON-shaped scoring rationale (article-style
  prose, then a numeric score) for each supplier, distinct per supplier.

The stub search provider returns 5 canned suppliers tagged with the requested
material + location, with realistic-looking source URLs.
