# Agent

## Agent Architecture Pattern

| Pattern | Use when |
|---------|----------|
| **Single-agent loop** | One LLM drives a deterministic tool-call loop. No branches, no handoffs. |
| **Graph (LangGraph)** | Multi-step pipeline with conditional edges, checkpointing, or parallel nodes. |
| **Multi-agent** | Specialised sub-agents with distinct roles; orchestrator routes between them. |
| **Supervisor** | One supervisor LLM dispatches to worker agents based on task type. |
| **Human-in-the-loop** | Execution pauses at defined checkpoints for user review or approval. |

**Chosen:** Single-agent tool-use loop. One Gemini model instance per turn drives a tool-call loop: it receives the user question + context, decides which tools to call, receives tool results, and synthesises a final response. No multi-agent orchestration or graph framework is needed because the conversation is linear and the branching is handled natively by the Gemini function-calling protocol.

**Patterns from `harness/patterns/agentic-ai.md` applied:**
- **Pattern 5 — Tool Use:** Core mechanic. Gemini calls `execute_sql`, `list_tables`, `describe_table`, `get_sample_rows`.
- **Pattern 8 — Memory Management:** Conversation history stored in SQLite; summary + sliding window keeps context within budget.
- **Pattern 16 — Resource-Aware Optimization:** Schema selection sub-call limits schemas injected into the prompt when the catalogue is large (>5 datasets).
- **Pattern 18 — Guardrails / Safety:** Destructive-SQL guard in the Python tool dispatcher before any DuckDB execution.
- **Pattern 12 — Exception Handling and Recovery:** Tool errors returned to Gemini as structured tool results; Gemini may retry with corrected SQL up to the round limit.

---

## LLM Provider & Model

| Role | Provider | Model ID | SDK |
|------|----------|----------|-----|
| Main agent loop | Google Gemini | `gemini-2.0-flash` | `google-genai` |
| Schema-selection sub-call | Google Gemini | `gemini-2.0-flash` | `google-genai` |
| Conversation summarisation | Google Gemini | `gemini-2.0-flash` | `google-genai` |

**API SDK:** `google-genai` Python package. Key: `GEMINI_API_KEY` from `.env`. Model is configurable via `LLM_MODEL` env var (default `gemini-2.0-flash`).

**Fallback behaviour:** None. If the Gemini API returns an error, the chat endpoint returns HTTP 502 with a user-visible message. No automatic retry. No stub provider in any code path.

**Prompt strategy:** System/user split. System prompt is a static string constant in `agent/prompts.py`. User turns and assistant turns are passed in the `contents` list using `google-genai` SDK conventions (`types.Content` with `role="user"` / `role="model"`). Tool results are passed as `role="user"` with `types.Part.from_function_response(...)` per the google-genai SDK. Structured output is not used — the final response is free-form markdown.

---

## Tools & Tool Calling

The following tools are defined as `types.FunctionDeclaration` objects in `agent/tools.py` and dispatched by `dispatch_tool_call()`.

| Tool name | Description | Inputs | Output shape | Side-effects |
|-----------|-------------|--------|--------------|--------------|
| `execute_sql` | Run a DuckDB SELECT query; return rows as JSON | `sql: str` | `{"rows": [...], "row_count": int, "error": str\|null}` | Reads DuckDB; destructive-SQL guard runs first |
| `list_tables` | List all active DuckDB tables with row counts | _(none)_ | `{"tables": [{"table_name": str, "row_count": int}]}` | None |
| `describe_table` | Schema + null count per column for a named table | `table_name: str` | `{"table_name": str, "columns": [{"name": str, "dtype": str, "null_count": int}]}` | Two lightweight DuckDB SELECTs |
| `get_sample_rows` | First N rows of a table | `table_name: str`, `n: int` (default 5) | `{"table_name": str, "rows": [...]}` | One DuckDB SELECT LIMIT |

**Destructive-SQL guard** (implemented in `agent/tools.py`, called by `execute_sql` before DuckDB):
```python
DESTRUCTIVE_KEYWORDS = {"DROP", "DELETE", "TRUNCATE", "ALTER"}

def is_destructive(sql: str) -> bool:
    normalised = " ".join(sql.upper().split())
    return any(kw in normalised.split() for kw in DESTRUCTIVE_KEYWORDS)
```
If `is_destructive` returns `True`, the tool returns `{"rows": [], "row_count": 0, "error": "Destructive SQL is not permitted. Only SELECT statements are allowed."}` without invoking DuckDB.

**Result truncation:** `execute_sql` caps result sets at 1,000 rows. Sets `was_truncated = True` in the turn state when capping occurs.

**Round limit:** If `tool_call_rounds > MAX_TOOL_ROUNDS` (default 10), the loop exits and returns a "could not complete analysis" message.

---

## Agent State

State is not held in a typed LangGraph state object — it is assembled per-turn from SQLite and passed to Gemini as a messages list.

```
Per-turn context (assembled before first Gemini call):
  system_prompt     : str               — SYSTEM_PROMPT constant from prompts.py
  prompt_history    : list[dict]        — [{role, content}, ...] from conversation_turns
                                          (summary_turn + last SUMMARY_KEEP_TURNS turns)
  relevant_schemas  : list[dict]        — [{table_name, columns}] from context builder
  tool_definitions  : list[FunctionDeclaration]  — the 4 tools, in google-genai format

Mutable within a turn (not persisted until turn ends):
  messages          : list[Content]     — the full conversation so far this turn, grows
                                          as tool calls and results are appended
  tool_call_rounds  : int               — incremented per Gemini-invocation round
  all_sql_executed  : list[str]         — SQL strings from all execute_sql calls
  datasets_touched  : set[str]          — table names referenced across all SQL calls
  result_set        : list[dict]        — rows from the last execute_sql call
  was_truncated     : bool              — true if last result_set was capped at 1,000
  last_sql          : str | None        — last SQL executed (for audit log)
  sql_error         : str | None        — DuckDB error from the last failing call
```

The per-turn mutable state is encapsulated in a `TurnState` dataclass in `agent/runner.py`, initialised at the start of each call to `run_turn()` and discarded after the audit log is written.

---

## Implementation: `agent/runner.py` — `run_turn()`

```python
# Pseudocode for run_turn(session_id: str | None, message: str) -> TurnResult
# (~60 lines of logic; details elided for brevity)

async def run_turn(session_id: str | None, message: str) -> TurnResult:
    start_ms = now_ms()

    # Step 1 — Load or create session
    with db_session() as db:
        session = load_or_create_session(db, session_id)
        session_id = session.id
        turns = load_history_window(db, session_id)
        # turns = [summary_turn?] + last SUMMARY_KEEP_TURNS non-summarised turns

    # Step 2 — Select relevant schemas
    all_datasets = load_active_datasets(db)
    if len(all_datasets) > 5:
        selected_names = await select_relevant_schemas(message, all_datasets)
        relevant = [d for d in all_datasets if d.table_name in selected_names]
    else:
        relevant = all_datasets

    # Step 3 — Build initial messages list
    schema_block = format_schemas(relevant)
    user_content = f"{schema_block}\n\nQuestion: {message}"
    messages = build_messages(turns, system_prompt=SYSTEM_PROMPT,
                              user_content=user_content)

    # Step 4 — Tool-use loop (delegated to loop.py)
    state = TurnState()
    final_text = await gemini_tool_loop(messages, TOOL_DEFINITIONS, state)

    # Step 5 — Synthesise response (Gemini already returns markdown)
    response_markdown = final_text  # already markdown from Gemini

    # Step 6 — Persist
    with db_session() as db:
        save_turn(db, session_id, role="user", content=message)
        save_turn(db, session_id, role="assistant", content=response_markdown)
        update_session_last_active(db, session_id)
        if state.all_sql_executed:
            write_audit_log(db, session_id, message, state, now_ms() - start_ms)
        maybe_summarise(db, session_id)  # triggers if total turns > MAX_HISTORY_TURNS

    # Step 7 — Return
    return TurnResult(
        session_id=session_id,
        response_markdown=response_markdown,
        generated_sql=state.last_sql,
        datasets_touched=sorted(state.datasets_touched),
        row_count_returned=len(state.result_set),
        latency_ms=now_ms() - start_ms,
    )
```

## Implementation: `agent/loop.py` — `gemini_tool_loop()`

```python
# Pseudocode for the Gemini tool-use loop

async def gemini_tool_loop(
    messages: list[Content],
    tool_definitions: list[FunctionDeclaration],
    state: TurnState,
) -> str:
    client = get_gemini_client()   # initialised once; key from settings
    tool_config = types.Tool(function_declarations=tool_definitions)

    while state.tool_call_rounds <= MAX_TOOL_ROUNDS:
        response = client.models.generate_content(
            model=settings.llm_model,
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[tool_config],
            ),
        )

        candidate = response.candidates[0]

        # Check for final text response (no more tool calls)
        if not has_function_calls(candidate):
            return extract_text(candidate)

        # Dispatch each function call
        tool_results = []
        for fn_call in get_function_calls(candidate):
            result = dispatch_tool_call(fn_call.name, fn_call.args, state)
            tool_results.append(
                types.Part.from_function_response(name=fn_call.name, response=result)
            )

        # Append model response + tool results to messages
        messages.append(types.Content(role="model", parts=candidate.content.parts))
        messages.append(types.Content(role="user", parts=tool_results))
        state.tool_call_rounds += 1

    # Round limit exceeded
    return ROUND_LIMIT_MESSAGE
```

## Agent Loop — Step Diagram (ASCII)

```
  run_turn() called
        │
        ▼
  ┌─────────────────────┐
  │ Step 1: Load/create │
  │ session + history   │
  └────────┬────────────┘
           │
           ▼
  ┌─────────────────────┐
  │ Step 2: Select      │
  │ relevant schemas    │
  │ (Gemini sub-call    │
  │  if >5 datasets)    │
  └────────┬────────────┘
           │
           ▼
  ┌─────────────────────┐
  │ Step 3: Build       │
  │ messages list       │
  │ (system + history   │
  │  + schemas + query) │
  └────────┬────────────┘
           │
           ▼
  ┌─────────────────────────────────────────────────────────┐
  │ Step 4: gemini_tool_loop()                              │
  │                                                         │
  │   ┌──────────────────────────────────────────────────┐  │
  │   │  Call Gemini generate_content(messages, tools)   │  │
  │   └─────────────────────┬────────────────────────────┘  │
  │                         │                               │
  │              ┌──────────▼──────────┐                    │
  │              │ Response has        │                     │
  │              │ function calls?     │                     │
  │              └──────────┬──────────┘                    │
  │                    No   │   Yes                         │
  │              ┌──────────▼──────────┐                    │
  │              │ rounds > MAX?       │                     │
  │              └──────────┬──────────┘                    │
  │                    Yes  │                               │
  │                    ┌────▼────┐                          │
  │                    │ Return  │                          │
  │                    │ limit   │                          │
  │                    │ message │                          │
  │                    └─────────┘                          │
  │                         │ No (has function calls)       │
  │              ┌──────────▼──────────────────────────┐    │
  │              │ dispatch_tool_call() for each call   │    │
  │              │ ┌────────────────────────────────┐   │    │
  │              │ │ execute_sql?                   │   │    │
  │              │ │  → destructive guard           │   │    │
  │              │ │  → DuckDB execute              │   │    │
  │              │ │  → update TurnState            │   │    │
  │              │ ├────────────────────────────────┤   │    │
  │              │ │ list_tables / describe_table / │   │    │
  │              │ │ get_sample_rows                │   │    │
  │              │ │  → DuckDB query                │   │    │
  │              │ └────────────────────────────────┘   │    │
  │              └──────────┬──────────────────────────┘    │
  │                         │                               │
  │              ┌──────────▼──────────┐                    │
  │              │ Append tool results │                     │
  │              │ to messages list    │                     │
  │              │ rounds += 1         │                     │
  │              └──────────┬──────────┘                    │
  │                         │                               │
  │                    ┌────▼────┐  rounds <= MAX            │
  │                    │ Loop ◄──┘                          │
  │                    └─────────┘                          │
  │                         │ (text response, no fn calls)  │
  │              ┌──────────▼──────────┐                    │
  │              │ Return final text   │                     │
  └──────────────┴─────────────────────┘────────────────────┘
           │
           ▼
  ┌─────────────────────┐
  │ Step 5: Synthesise  │
  │ response_markdown   │
  │ (Gemini text is     │
  │  already markdown)  │
  └────────┬────────────┘
           │
           ▼
  ┌─────────────────────┐
  │ Step 6: Persist     │
  │ • user turn         │
  │ • assistant turn    │
  │ • update session    │
  │ • audit log (if SQL)│
  │ • maybe_summarise() │
  └────────┬────────────┘
           │
           ▼
  ┌─────────────────────┐
  │ Step 7: Return      │
  │ TurnResult          │
  └─────────────────────┘
```

---

## Agent State

State is not held in a typed LangGraph state object — see the `TurnState` dataclass description above.

---

## Tools — Implementation Notes

### `execute_sql`

```python
def execute_sql(sql: str, state: TurnState) -> dict:
    if is_destructive(sql):
        return {"rows": [], "row_count": 0,
                "error": "Destructive SQL is not permitted. Only SELECT statements are allowed."}
    try:
        with duckdb_service.lock:
            rows = duckdb_service.conn.execute(sql).fetchdf().to_dict("records")
        was_truncated = len(rows) > MAX_RESULT_ROWS
        rows = rows[:MAX_RESULT_ROWS]
        state.all_sql_executed.append(sql)
        state.last_sql = sql
        state.result_set = rows
        state.was_truncated = was_truncated
        # Extract table names from SQL (simple regex over FROM/JOIN clauses)
        state.datasets_touched.update(extract_table_names(sql))
        return {"rows": rows, "row_count": len(rows), "error": None,
                "was_truncated": was_truncated}
    except Exception as exc:
        state.sql_error = str(exc)
        state.all_sql_executed.append(sql)
        state.last_sql = sql
        return {"rows": [], "row_count": 0, "error": str(exc)}
```

---

## Memory & Context

| Scope | Mechanism | What is stored |
|-------|-----------|----------------|
| Within a turn | `TurnState` dataclass (in-memory) | Tool call history, result sets, SQL strings, round counter |
| Across turns (same session) | SQLite `conversation_turns` | User and assistant messages; summary messages |
| Across server restarts | SQLite (all tables) | Sessions, turns, datasets, audit log |
| Dataset schemas | SQLite `datasets.schema_json` | Column names and types per dataset |
| DuckDB table registry | In-process DuckDB (rebuilt from SQLite on startup) | File-backed table views |

**Context window management:** Summary + sliding window.
- When `len(non-summarised turns for session) > MAX_HISTORY_TURNS` (default 20): call Gemini with a summarisation prompt to produce a 3–5 sentence compact summary; insert the summary as a new `ConversationTurn` row with `role = "system"`; mark the summarised turns with `is_summarised = true`.
- The prompt history sent to Gemini is always: `[summary_turn if any] + [last SUMMARY_KEEP_TURNS turns where is_summarised = false]`.
- `MAX_HISTORY_TURNS = 20` and `SUMMARY_KEEP_TURNS = 6` are configurable via env vars.

**Schema selection:**
- If `len(active datasets) <= 5`: include all schemas in the prompt (no sub-call).
- If `len(active datasets) > 5`: send a short Gemini sub-call (no tools, text-only) asking which table names from the full list are relevant to the user question. Use only those schemas. On sub-call failure: fall back to all schemas and log a warning.

---

## System Prompt

Stored as `SYSTEM_PROMPT` constant in `agent/prompts.py`. Must remain ≤500 tokens.

```
You are a senior data analyst assistant. You have access to the user's uploaded datasets as DuckDB tables.

Your behaviour:
1. CLARIFY before querying: if the question is ambiguous (multiple matching tables, undefined metric), ask ONE focused clarifying question. Do not guess.
2. DECOMPOSE complex questions: use multiple execute_sql calls for multi-step analyses.
3. DATA QUALITY: after querying, note any NULL-heavy columns, type mismatches, or outliers you observe in the results.
4. FOLLOW-UP: end every answer (not clarifying questions) with "**You might also ask:**" followed by 2-3 bullet-point suggestions.
5. SAFETY: never generate DROP, DELETE, TRUNCATE, or ALTER statements. If asked, explain politely that you cannot perform destructive operations.
6. FORMAT: respond in markdown. Use tables for result sets. Be concise.

When you need to understand the data, use list_tables, describe_table, or get_sample_rows before writing SQL.
Result sets larger than 20 rows: show first 20 rows in the markdown table and note the total count.
```

---

## Human-in-the-Loop Checkpoints

None. The agent does not pause for human approval. Clarifying questions are surfaced as chat messages; the user's reply is the next chat turn.

---

## Error Handling & Recovery

**Turn-level:**
- Gemini API failure (4xx/5xx/network) → HTTP 502; no turn written to `conversation_turns`; no audit log entry.
- DuckDB error in `execute_sql` → returned to Gemini as `{"rows": [], "row_count": 0, "error": "<message>"}` tool result; Gemini may retry with corrected SQL.
- Tool call round limit (10) exceeded → agent returns: `"I was unable to complete the analysis in the allowed number of steps. Please rephrase your question."` Turn IS written to SQLite (both user and this assistant message).
- Audit log write failure → logged to stdout; chat response still returned (audit failure is non-fatal).
- Schema-selection sub-call failure → fall back to all schemas; log WARNING; continue.

**Startup:**
- SQLite file unreadable → fatal; server fails to start with clear error message.
- `data/uploads/` absent → created on startup.
- DuckDB registration failure for a dataset at startup → logged WARNING; dataset skipped in-memory (not soft-deleted in SQLite); will retry on next restart.
- `GEMINI_API_KEY` absent → fatal; settings validation fails at startup with clear message pointing to `.env`.

**Resumption:** No run resumption. Each HTTP request is a complete, independent turn. Failed turns can be retried by the user.

---

## Concurrency Model

- **HTTP:** FastAPI async event loop + Uvicorn handles multiple concurrent HTTP requests.
- **DuckDB:** Singleton `DuckDBService` with a `threading.Lock`. Lock acquired for every DuckDB call (register view, execute query, health check). DuckDB supports concurrent reads natively, but the lock prevents concurrent `CREATE OR REPLACE VIEW` registration (upload path) from racing with queries. All table registrations are writes; all queries are reads.
- **SQLite:** SQLAlchemy connection pool. WAL mode enabled at startup (`PRAGMA journal_mode=WAL`) to allow concurrent reads during writes.
- **Agent loop:** Each chat request runs its own `run_turn()` call independently. No shared in-process mutable state between turns (all turn state in `TurnState` is local to the call).

---

## Observability

| Signal | What | Where |
|--------|------|-------|
| Request log | HTTP method, path, status, latency | FastAPI default stdout logging |
| Agent turn log | session_id, turn_index, tool calls, SQL executed, latency_ms | stdout JSON line per turn (structlog or stdlib logging) |
| Gemini API errors | Full error response, model, session_id | stdout ERROR log |
| DuckDB errors | SQL attempted, error message, session_id | stdout ERROR log |
| Audit log | Full turn record | SQLite `audit_log` table |

No external tracing or APM in v1. Logs written to stdout; captured by terminal.
