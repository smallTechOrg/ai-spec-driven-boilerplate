# Capability: conversation

## What It Does
Lets the user hold a multi-turn chat against a dataset where each new question is answered with awareness of prior turns (turn memory), and persists the full conversation and run history across sessions.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| dataset_id | string | user selection | yes |
| question | string | user (ask box) | yes |
| conversation_id | string | path | for follow-up turns |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| Conversation | row | `conversations` ([data.md](../data.md)) |
| Messages | user + assistant turns | `messages`; UI transcript |
| Threaded history | prior `{question, result_summary}` summaries | fed into [analyze_dataset](analyze_dataset.md) as `history` |
| Run history | persisted runs per thread | `analysis_runs`; `GET /runs?conversation_id=` |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| (none new) | reuses analyze_dataset's Gemini calls with prior-turn context | as analyze_dataset |

## Business Rules
- Memory threaded to the LLM is **prior-turn summaries only** (question + bounded computed result) — **never raw rows**.
- Conversations, messages, and run history persist across server restarts (SQLite).
- A follow-up like "now break that down by month" is answered using the prior turn's context.
- Context is bounded: if a thread grows large, oldest turns are summarised/dropped (sliding window).
- Each assistant message links to the `analysis_run` that produced it (code/result/tokens/cost traceable).

## Success Criteria
- [ ] A second question that references the first ("break that down by month") produces an answer consistent with the prior turn's result.
- [ ] After a page reload (and a server restart) the full transcript and run history reload from SQLite.
- [ ] The history threaded into the prompt contains no raw rows (asserted).
- [ ] `GET /conversations/{id}` returns all turns in order with their linked runs.
