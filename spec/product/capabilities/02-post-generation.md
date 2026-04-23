# Capability: Post Generation

## What It Does

Generates a full blog post (title + structured body in Markdown) for a given topic, written in the voice of an assigned writer persona.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|---------|
| topic | str | Topic discovery output | yes |
| writer | Writer | DB (selected by assignment) | yes |
| blog_name | str | Blog config | yes |
| blog_niche | str | Blog config | yes |
| target_word_count | int | Hardcoded: 800–1500 words | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| title | str | Post record |
| content_markdown | str | Post record |
| content_html | str | Post record (rendered from markdown) |
| slug | str | Post record + HTML filename |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini API (text) | Generate post with writer persona as system prompt | Retry once; if still fails, mark post as failed and continue with remaining posts |

## Prompt Structure

The LLM call uses two layers:
- **System prompt:** `writer.persona_prompt` — defines voice, style, expertise
- **User prompt:** Instruction to write a blog post on `{topic}` for `{blog_name}`, targeting `{word_count}` words, with intro + at least 3 subheadings + conclusion

## Business Rules

- Post must have: a title, an introduction paragraph, at least 3 `##` subheadings, and a conclusion
- Word count target: 800–1500 words (Gemini is instructed; not strictly enforced — posts between 600–2000 words are acceptable)
- Slug is derived from the title: lowercased, spaces → hyphens, special chars stripped, max 60 chars, suffix `-YYYY-MM` to ensure uniqueness
- Markdown is rendered to HTML using a standard Markdown library (no custom extensions)
- Writer persona is injected as the system prompt; the blog niche is mentioned in the user prompt to keep content on-topic

## Success Criteria

- [ ] Output contains a title, at least 3 `##` headings, and a conclusion section
- [ ] Word count is between 600 and 2000 words
- [ ] Slug is unique within the database (no two posts share a slug)
- [ ] Content HTML is valid HTML (parseable by an HTML parser without errors)
- [ ] On Gemini failure, post is marked failed and remaining posts in the run continue
