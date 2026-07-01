# Capability: Conversational Q&A

## What It Does

User types a natural-language question about their uploaded CSV. The agent generates Python/pandas code, executes it server-side, and returns a prose answer with optional Plotly chart. Full conversation history is preserved and used for follow-up questions.

## Input

- Natural-language question string (POST /sessions/{session_id}/messages)
- Session context: uploaded file profiles (schema + stats) and last 10 conversation turns from DB

## Output

- `content`: plain prose answer written for a non-technical reader
- `chart_json`: optional Plotly figure JSON (null if no chart generated)

## LLM Prompt Strategy (privacy-preserving)

Gemini receives ONLY:
1. System instruction for pandas code generation
2. Schema: column names + dtypes (NO raw rows)
3. Stats: numeric min/max/mean/std/percentiles, categorical top-5 value_counts, null counts
4. Last 10 conversation turns (user questions + assistant answers)
5. Current question

Raw row values are NEVER included in any LLM prompt.

## Conversation History

- All turns stored in SQLite `messages` table
- Last 10 turns loaded on each Q&A call for context
- Trimmed to 10 turns to control token costs
- No cross-session memory

## Uncertainty Handling

- Ambiguous column: generate code for most likely match + state assumption inline
- Ambiguous aggregation: state assumption inline ("I'm summing by month — let me know if you want a different grouping")
- Phase 3: structured clarification flow

## Phase

Phase 1 (real). Multi-turn context real from Phase 1.

## Acceptance Criteria

- [ ] "Show me revenue by month" → bar chart with months on x-axis
- [ ] Follow-up "now show only Q1" → filtered correctly using conversation context
- [ ] Question about nonexistent column → helpful error message, no crash
- [ ] LLM prompt never contains raw row values (verified by automated test)
