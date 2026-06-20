# Capability: Summarize a ticket thread  ·  Priority: P3

> A deterministic, journey-complete, spec-registered **STUB**. Wired into the graph and reachable end-to-end,
> but returns a fixed contract instead of doing the real summarization. Promoted to a real implementation in a
> follow-up build via `/spec-new-capability`.

## What & why

A long back-and-forth ticket thread should be reducible to its single open question so a rep can pick it up
fast. Serves the "a long thread can be summarized to its open question" success criterion in
`spec/product.md`. **Stub contract until promoted:** the `summarize_thread` tool returns a fixed, well-formed
summary record — `{"open_question": <sentinel>, "messages_seen": <count>}` — so the journey is complete and
the capability is registered, even though no real summarization model call is wired yet.

## Acceptance criteria (EARS — these ARE the eval inputs)

- WHEN a ticket thread is summarized the system SHALL return a summary record stating the open question and the number of messages seen. [@eval: tests/test_summarize_thread_gate.py::test_summary_returns_open_question]

## Tools & layers touched
- tool: summarize_thread  (in-process @tool, STUB — `harness/patterns/tools-and-mcp.md`)
- layers: base ReAct loop only

## Evaluation
- outcome evaluation_steps:
  - Does the summary record state an open question?
  - Does it report a count of messages seen?
- expect_tools: [summarize_thread]
- forbid_tools: []   # the stub is non-mutating; it returns a fixed record.
