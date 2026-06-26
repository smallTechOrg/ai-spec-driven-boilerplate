# Capability: CSV Analysis

## What It Does

Accepts a CSV file upload, loads it into an in-memory pandas DataFrame, and answers a natural-language question about the data by sending the column schema and sample rows to Gemini and returning a plain-English text answer.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `file` | multipart/form-data binary | Browser file picker | Yes (upload step) |
| `session_id` | UUID string | `POST /sessions` response | Yes (question step) |
| `question` | string (1–2000 chars) | User chat input | Yes (question step) |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `session_id` | UUID string | JSON response → browser session state |
| `columns` | `list[{name: str, dtype: str}]` | JSON response → upload panel schema display |
| `row_count` | integer | JSON response → upload panel |
| `run_id` | UUID string | JSON response → browser |
| `answer` | string | JSON response → chat panel answer card |
| `node_trace` | `list[str]` | JSON response → answer card (Phase 2 trace display) |
| `status` | `"completed"` | `"failed"` | JSON response + SQLite |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| In-memory store | `SESSION_STORE[session_id]` write (upload) | HTTP 500 — should not fail under normal conditions |
| In-memory store | `SESSION_STORE[session_id]` read (question) | Fatal pipeline error: `status="failed"`, `error="Session not found"` |
| Gemini API (`gemini-2.0-flash`) | `LLMClient.complete(system_prompt, user_message)` | Fatal pipeline error: `status="failed"`, `error` set to API error message |
| SQLite | `Session` row insert | HTTP 500 with structured error |
| SQLite | `ConversationRun` row insert + update | Logged; pipeline result still returned to client |

## Business Rules

- CSV file size limit: 50 MB. Files over 50 MB return HTTP 413.
- Column limit: 200. Files with more than 200 columns return HTTP 422.
- The CSV must have a header row. Files without a header row return HTTP 422.
- The DataFrame is stored only in memory for the lifetime of the server process. A process restart loses all session data.
- The Gemini prompt includes the full column schema and the first 10 rows of the DataFrame. For DataFrames with more than 50 columns, sample row values are omitted and only the schema is sent.
- Each question is stateless: prior answers are not included in the Gemini prompt.
- `answer_question` returns the raw Gemini text response as the answer — no post-processing or summarisation.

## Success Criteria

- [ ] A valid CSV upload returns HTTP 200 with `session_id`, `columns`, and `row_count` within 3 seconds for files up to 10 MB.
- [ ] The DataFrame is present in `SESSION_STORE` after upload and can be retrieved by `session_id`.
- [ ] A natural-language question returns a non-empty `answer` string within 15 seconds against the real Gemini API.
- [ ] `status` is `"completed"` and `node_trace` contains `["parse_csv", "answer_question", "finalize"]` on a successful run.
- [ ] An upload with a non-CSV file returns HTTP 422 with a human-readable error message.
- [ ] A question with an invalid `session_id` returns HTTP 200 with `status="failed"` and a readable `error` field.
- [ ] The CSV data is never written to any file on disk during or after upload.
