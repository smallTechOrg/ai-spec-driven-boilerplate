# Agent Graph

LangGraph pipeline for the Lead Gen Agent. Linear `search → extract → score → persist` with an explicit `error` short-circuit.

## State

```python
class AgentState(TypedDict, total=False):
    # Identity
    run_id: str

    # Input filters
    country: str
    industry: str
    size_band: str

    # Pipeline data (populated progressively)
    search_results: list[dict]       # raw search hits: {title, url, snippet}
    candidates: list[Candidate]      # after extract
    leads: list[Lead]                # after score

    # Terminal
    status: str                      # "completed" | "failed"
    error: str | None                # set on fatal failure
```

## Nodes

### `search_node`

**Reads from state:** `country`, `industry`, `size_band`
**Writes to state:** `search_results`
**External calls:** `SearchTool.search(query)` — DuckDuckGo HTML scrape in v0.1.
**Prompt tag:** `<node:search>` (not used by LLM; reserved for tool adapter logs).
**Failure:** sets `error` and short-circuits.

### `extract_node`

**Reads from state:** `search_results`, `country`, `industry`, `size_band`
**Writes to state:** `candidates`
**External calls:** `LLMClient.complete(prompt)` — prompt carries `<node:extract>` tag. Stub returns article-shaped JSON-lines with firmographic fields.
**Failure:** sets `error`.

### `score_node`

**Reads from state:** `candidates`
**Writes to state:** `leads`
**External calls:** `LLMClient.complete(prompt)` — prompt carries `<node:score>` tag. Stub returns a number 0–100 + rationale.
**Rubric signals:** size band, industry, visible tech-stack poverty, absence of data-role job postings.

### `persist_node`

**Reads from state:** `leads`, `run_id`
**Writes to state:** `status`
**External calls:** `repository.add_lead()`, `repository.complete_run()`
**Failure:** sets `error`; run marked `failed`.

## Edges

```
START → search_node
search_node   --(error?)--> persist_node (mark failed)
search_node   --(ok)-->     extract_node
extract_node  --(error?)--> persist_node (mark failed)
extract_node  --(ok)-->     score_node
score_node    --(error?)--> persist_node (mark failed)
score_node    --(ok)-->     persist_node
persist_node  → END
```

## Stub Behaviour

The stub LLM branches purely on `<node:*>` tags in the prompt (never on prose keywords — per non-negotiable rule 8):

- `<node:extract>` → returns a fixed list of article-shaped firmographic records (3 candidates with name, website, HQ city, short description paragraph).
- `<node:score>` → returns `{"score": <int>, "rationale": "<one sentence>"}` deterministically derived from the candidate name hash.

## UI Banner

When `settings.resolved_llm_provider == "stub"`, every rendered page shows a banner. Injected into every template context as `llm_provider`.
