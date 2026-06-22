# Capability: Token Economy

## What It Does

Keeps Gemini's input prompt within token budget by selecting only the schemas of tables relevant to the current question, keeping the system prompt compact, and summarising old conversation turns once the history exceeds a configured turn limit.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| user_message | string | Chat API request | Yes |
| all_dataset_schemas | JSON array of `{table_name, columns: [{name, dtype}]}` | SQLite `datasets` table (all active datasets) | Yes |
| conversation_turns | array of `{role, content, turn_index}` | SQLite `conversation_turns` for this session | Yes |
| MAX_HISTORY_TURNS | integer (env var, default 20) | Application config | Yes |
| SUMMARY_KEEP_TURNS | integer (env var, default 6) | Application config | Yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| relevant_schemas | JSON array of `{table_name, columns}` | Passed to NL→SQL capability as context |
| prompt_history | array of `{role, content}` | Passed to Gemini as conversation history |
| summary_written | boolean | Internal; triggers SQLite update if true |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini API | `generate_content` with a table-selection sub-prompt (identify relevant tables from dataset list + user question) | Fall back to including all schemas; log warning |
| SQLite (via SQLAlchemy) | UPDATE `conversation_turns`: insert summary row, mark summarised turns as `is_summarised = true` | Log error; continue with full history (may exceed budget) |

## Business Rules

- **Schema selection:** The Context Builder sends a lightweight Gemini call (no tools, just text) asking which table names from the full catalogue are relevant to the current question. Only those schemas are included in the main agent prompt. If the catalogue has ≤5 tables, all schemas are always included (no selection call needed).
- **Schema format:** Each included schema is formatted as a compact block: `Table: <table_name>\nColumns: col1 (dtype), col2 (dtype), ...`. No sample data or null counts are included at this stage (those are fetched on-demand via tools).
- **History window:** The conversation is always represented as: `[optional_summary_message] + [last SUMMARY_KEEP_TURNS turns]`. When `len(turns) > MAX_HISTORY_TURNS`, the oldest `(MAX_HISTORY_TURNS - SUMMARY_KEEP_TURNS)` turns are summarised by calling Gemini with a summarisation prompt, and the summary is stored as a single `conversation_turns` row with `role = "system"` and `is_summarised = true`. Summarised turns have `is_summarised = true` and are excluded from future history windows.
- **Summary prompt:** The summarisation call instructs Gemini to produce a compact 3–5 sentence summary of the conversation so far, preserving key facts (datasets mentioned, conclusions reached, pending questions).
- **Compact system prompt:** The system prompt is stored as a static template in the codebase (not in the database). It must be ≤500 tokens. See [spec/agent.md](../agent.md) for the full outline.
- Token counting is not performed explicitly (no tiktoken or Gemini token-count API call per turn); the budget is managed through the turn-count heuristic only.

> **Assumed:** The table-selection sub-call uses the same Gemini model (`gemini-2.0-flash`) as the main agent. This is acceptable because the sub-call is short (table names + one-sentence question) and does not require a cheaper model.

> **Assumed:** `MAX_HISTORY_TURNS = 20` and `SUMMARY_KEEP_TURNS = 6` are the defaults. Both are overridable via environment variables.

## Success Criteria

- [ ] When a session has more than `MAX_HISTORY_TURNS` turns, the next chat call triggers a summarisation: a new `conversation_turns` row with `role = "system"` is written, and the summarised turns have `is_summarised = true`.
- [ ] The prompt sent to Gemini for the main agent call contains at most `SUMMARY_KEEP_TURNS` turn messages (plus one optional summary message) — verified by inspecting the messages list before the Gemini call.
- [ ] When a catalogue has 3 active datasets and the question clearly references one by name, only 1 schema is included in the agent prompt (verified by inspecting context).
- [ ] When the catalogue has ≤5 datasets, no schema-selection Gemini sub-call is made (verified by call count).
- [ ] A failure in the schema-selection sub-call falls back to including all schemas without raising an exception.
- [ ] Summarised turns (`is_summarised = true`) are not included in the `prompt_history` array sent to Gemini.
