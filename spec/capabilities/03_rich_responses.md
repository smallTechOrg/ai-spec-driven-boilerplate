# Capability: Rich Responses

## What It Does

Formats the SQL result set and Gemini's analytical narrative into a structured markdown response — including a result table and a concise plain-English explanation — and returns it to the user via the chat API.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| gemini_response_text | string (markdown) | Gemini final text output (after tool-use rounds) | Yes |
| result_set | JSON array of row objects | DuckDB execution result from NL→SQL capability | No (null if no SQL was run) |
| row_count_returned | integer | DuckDB execution result | No |
| was_truncated | boolean | NL→SQL capability (true if result > 1,000 rows) | No |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| response_markdown | string | Chat API response body; stored in SQLite `conversation_turns` as assistant turn |
| display_row_count | integer | Embedded in response_markdown |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| None | — | — |

## Business Rules

- The response is always rendered as markdown. The frontend renders it via a markdown parser (no sanitisation of user-controlled HTML needed because the source is the LLM, not the user).
- If a result set is present, the response must contain a markdown table with column headers and up to 20 rows displayed inline. If the result has more than 20 rows, the table shows the first 20 and a note reads: `Showing 20 of <N> rows.`
- If `was_truncated` is true (result was capped at 1,000 rows by the execution layer), the response includes a note: `Query returned more than 1,000 rows; results were truncated to 1,000.`
- If no result set is present (Gemini asked a clarifying question or returned a narrative-only answer), the response contains only the Gemini text.
- If the result set is empty (zero rows), the response contains the markdown table header with no data rows and a narrative note: `The query returned no results.`
- Gemini is responsible for the narrative content (interpretation, quality notes, follow-up suggestions). The Response Synthesiser only assembles the final string from Gemini's output and the result set; it does not add its own narrative.
- The `response_markdown` stored in `conversation_turns` is identical to what is returned to the client — no post-processing is applied after storage.

> **Assumed:** Charts and dashboard rendering are out of scope for v1. The response is markdown-only. Any Gemini output that includes code fences for chart specifications is passed through as literal markdown code blocks (not rendered as charts).

## Success Criteria

- [ ] A question with a non-empty result set produces a response containing a markdown table with correct column headers and data values.
- [ ] A result set with more than 20 rows produces a table showing exactly 20 rows and the `Showing 20 of N rows` note.
- [ ] A zero-row result set produces a response with a table header only and the "no results" note; no error is thrown.
- [ ] A response where Gemini asks a clarifying question (no result set) contains only the question text and no empty table.
- [ ] The `response_markdown` field in the stored `conversation_turns` row is identical to the value returned in the API response body.
- [ ] Truncation note appears when `was_truncated = true`.
