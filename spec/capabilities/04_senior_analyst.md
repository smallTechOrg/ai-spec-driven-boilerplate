# Capability: Senior Analyst Workflow

## What It Does

Equips the agent with senior-analyst behaviours: it proactively clarifies ambiguous questions before querying, decomposes multi-step questions into sub-queries, surfaces data quality notes (nulls, type mismatches, outliers) in its narrative, suggests follow-up questions after each answer, and refuses destructive SQL.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| user_message | string | Chat API request | Yes |
| relevant_schemas | JSON array of `{table_name, columns: [{name, dtype, null_count, sample_values}]}` | Context Builder | Yes |
| system_prompt | string | Agent Loop (static template, see [spec/agent.md](../agent.md)) | Yes |
| conversation_history | array of `{role, content}` | SQLite `conversation_turns` | Yes |
| proposed_sql | string | Gemini tool call argument | Conditional (only for destructive-SQL guard) |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| clarifying_question | string or null | Response Synthesiser (if question is ambiguous) |
| data_quality_notes | string or null | Embedded by Gemini in narrative response |
| follow_up_suggestions | array of strings or null | Embedded by Gemini in narrative response |
| sql_refused | boolean | Returned to Gemini as tool error if destructive SQL detected |
| refusal_message | string or null | Response Synthesiser (when sql_refused = true) |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| DuckDB | `SELECT COUNT(*) - COUNT(<col>) FROM <table>` for null counts (called via `describe_table` tool) | Log and omit null counts from quality notes; do not abort |
| DuckDB | `SELECT <col> FROM <table> LIMIT 5` for sample values (called via `get_sample_rows` tool) | Log and omit samples; do not abort |

## Business Rules

- **Clarification:** If the user's question is ambiguous (could apply to multiple tables, or the metric is undefined), Gemini must ask one focused clarifying question before generating SQL. The system prompt instructs Gemini to treat ambiguity as a trigger for clarification, not a guess.
- **Decomposition:** For questions that require multiple steps (e.g., "what is the month-over-month growth rate?"), Gemini issues sequential `execute_sql` tool calls, each building on the previous result. It does not attempt to express the full logic in one SQL string when sub-queries would be clearer.
- **Data quality notes:** After executing SQL, Gemini is instructed (via system prompt) to include in its narrative: any NULL-heavy columns in the result, potential outliers if numeric columns show extreme variance, and type-mismatch warnings if a column expected to be numeric contains strings.
- **Follow-up suggestions:** Gemini is instructed to end every non-clarification response with 2–3 suggested follow-up questions, formatted as a bulleted list under the heading `**You might also ask:**`.
- **Destructive-SQL guard:** Before DuckDB executes any SQL string, the Python tool dispatcher checks whether the normalised (upper-cased, whitespace-collapsed) SQL contains any of the keywords: `DROP`, `DELETE`, `TRUNCATE`, `ALTER`. If found, the tool returns an error to Gemini: `"Destructive SQL is not permitted. Only SELECT statements are allowed."` This check is in the Python layer, not delegated to Gemini.
- The guard applies to all SQL generated in any tool-call round, including sub-queries and CTEs.
- The destructive-SQL guard is the only hard rule enforced in Python; all other analyst behaviours are directed via the system prompt.

> **Assumed:** Null counts and sample values are fetched lazily — only when Gemini calls `describe_table` or `get_sample_rows`. They are not pre-computed on upload (that would be too expensive for large files).

## Success Criteria

- [ ] Sending a question that matches two uploaded tables with similar column names causes the agent to ask a clarifying question naming both tables, without executing any SQL.
- [ ] A multi-step question (e.g., "what percentage of orders were returned last month vs. the month before?") results in at least two `execute_sql` tool calls in sequence.
- [ ] The narrative response for a query on a column with >10% NULLs contains a data quality note mentioning the NULL count.
- [ ] Every non-clarification response ends with a `**You might also ask:**` section containing 2–3 suggestions.
- [ ] A message such as "drop the sales table" or any variation that would produce destructive SQL causes the Python guard to reject the tool call and the user to receive a refusal message — verified by checking that DuckDB's execute function is never called with the destructive statement.
- [ ] The destructive-SQL guard catches `DELETE`, `TRUNCATE`, and `ALTER` in addition to `DROP`.
- [ ] A clarifying question turn does not write an audit log entry with a `generated_sql` field (no SQL was generated).
