# Capability: Topic Discovery

## What It Does

Selects N distinct blog topics for a generation run by combining niche-aware LLM brainstorming with Google Trends RSS signals, then filtering out topics already used in previous runs.

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
| Google Trends RSS (`https://trends.google.com/trends/trendingsearches/daily/rss?geo=US`) | Fetch daily trending searches; filter titles that match niche keywords | Skip trending step; use LLM-only candidates |

## Business Rules

- Must return exactly `posts_count` topics
- No topic in the output may appear in `used_topics` (case-insensitive, normalised)
- If fewer than `posts_count` unique candidates remain after deduplication, generate a second LLM batch with the instruction "suggest different angles on [niche]"
- Topics should be specific enough to write a focused 600–2000 word post (not "AI" but "How to automate your email inbox with AI in 2026")
- Trending signals are used to bias selection, not to override niche — all topics must still fit the niche

## Success Criteria

- [ ] Returns exactly `posts_count` topics
- [ ] No returned topic matches any string in `used_topics` (after normalisation)
- [ ] Each topic is a specific, writable blog post title or premise (not a one-word category)
- [ ] When Google Trends is unavailable, falls back gracefully and still returns `posts_count` topics
