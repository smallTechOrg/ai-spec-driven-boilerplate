# Capability: Topic Discovery

## What It Does

Selects N distinct blog topics for a generation run by combining niche-aware LLM brainstorming with real-time web search signals (DuckDuckGo + Tavily), then filtering out topics already used in previous runs.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|---------|
| blog_niche | str | Blog config | yes |
| themes | list[str] | Blog config | yes |
| posts_count | int | Run config | yes |
| used_topics | list[str] | UsedTopic table | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| selected_topics | list[str] | GenerationState (passed to post generation) |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini API (text) | Generate 10 candidate topics from niche + themes | Raise error; abort run |
| DuckDuckGo Search (via `duckduckgo-search` library) | Search `"{niche} trending topics {current_month}"` — returns titles and snippets | Skip DuckDuckGo; continue with other sources |
| Tavily Search API | Search `"{niche} latest trends {current_month}"` — returns richer, curated results | Skip Tavily; continue with other sources |

## Business Rules

- Must return exactly `posts_count` topics
- No topic in the output may appear in `used_topics` (case-insensitive, normalised)
- DuckDuckGo and Tavily searches run in parallel; results are pooled and deduplicated by title similarity
- Gemini selects final topics from the combined candidate pool (LLM brainstorm + DuckDuckGo + Tavily), filtered to those matching the niche
- If fewer than `posts_count` unique candidates remain after deduplication, Gemini generates a second batch with "suggest different angles on [niche]"
- Topics should be specific enough to write a focused post (not "AI" but "How to automate your email inbox with AI in 2026")
- Trending signals bias selection toward timely topics — all selected topics must still fit the niche

## Success Criteria

- [ ] Returns exactly `posts_count` topics
- [ ] No returned topic matches any string in `used_topics` (after normalisation)
- [ ] Each topic is a specific, writable premise (not a one-word category)
- [ ] When both DuckDuckGo and Tavily fail, falls back to LLM-only brainstorm and still returns `posts_count` topics
- [ ] When only one search source fails, the other is still used (partial failure is not total failure)
