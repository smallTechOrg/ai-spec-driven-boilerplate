# Capability: Chart Generation

## What It Does

Generates a matplotlib chart from the uploaded CSV data by having Gemini write pandas/matplotlib Python code, executing that code in a sandboxed environment, and returning the resulting chart as a base64-encoded PNG alongside the executed code.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `session_id` | UUID string | URL path parameter | Yes |
| `question` | string (1–2000 chars) | Request body | Yes |
| DataFrame | `pd.DataFrame` | In-memory `SESSION_STORE[session_id]` | Yes |
| `column_schema` | `list[{name, dtype}]` | `parse_csv` node output (AgentState) | Yes |
| `sample_rows` | `list[dict]` | `parse_csv` node output (AgentState) | Yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `chart_base64` | base64 string (PNG) | JSON response → browser chart panel |
| `chart_type` | `"bar"` | `"line"` | `"scatter"` | JSON response → browser alt text |
| `executed_code` | string | JSON response → browser code panel |
| `chart_data` | JSON in SQLite | `ConversationRun.chart_data` column |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini API (`gemini-2.0-flash`) | `LLMClient.complete()` with code-generation system prompt | Fatal pipeline error: `status="failed"` |
| Python `exec()` sandbox | Execute generated pandas/matplotlib code | Fatal pipeline error: `status="failed"`, traceback in `error` field |

## Business Rules

- Code generation uses `src/prompts/generate_code.md` to instruct Gemini to produce a self-contained Python code block that uses `df` (the DataFrame), `pd` (pandas), and `plt` (matplotlib.pyplot).
- Code execution uses a restricted `exec()` scope containing only: `df`, `pd`, `plt`, `io`. No `os`, `sys`, `subprocess`, `open`, `__import__`, or any builtin that can touch the filesystem or network.
- After execution, the sandbox checks for a `fig` variable (`matplotlib.figure.Figure`). If found, it is saved to a `BytesIO` buffer as PNG and base64-encoded.
- `chart_type` is inferred from the figure's axes after execution: checks for bar containers → `"bar"`, checks for line artists → `"line"`, checks for scatter collections → `"scatter"`. Defaults to `"bar"` if undetermined.
- If `exec()` raises any exception, `state["error"]` is set to the exception message and the pipeline routes to `handle_error`. The client receives `status="failed"` with the error text.
- If Gemini returns a response with no fenced code block, `state["error"]` is set to `"No executable code block found in Gemini response"`.
- The `chart_data` column in `ConversationRun` stores a JSON object: `{"chart_base64": "<base64>", "chart_type": "bar"}`.
- This capability is Phase 2 only. In Phase 1 the `chart_base64`, `chart_type`, and `executed_code` fields are always `null` in the response.

## Success Criteria

- [ ] A question that implies a chart (e.g. "Show me sales by region") returns a non-null `chart_base64` PNG and a non-null `executed_code` string in Phase 2.
- [ ] The base64 string decodes to a valid PNG image.
- [ ] `chart_type` is one of `"bar"`, `"line"`, or `"scatter"`.
- [ ] Malicious code injected via a question (e.g. a question containing `import os`) does not execute OS calls — the sandbox restricts imports to the explicit exec namespace.
- [ ] If the generated code raises a Python exception, the response has `status="failed"` and a readable `error` message; no 500 is returned.
- [ ] `ConversationRun.chart_data` is populated in SQLite with the base64 PNG and chart type after a successful run.
- [ ] `node_trace` on a successful Phase 2 run contains `["parse_csv", "generate_code", "execute_code", "answer_question", "finalize"]`.
