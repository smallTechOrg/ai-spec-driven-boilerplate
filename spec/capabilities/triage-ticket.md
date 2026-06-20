# Capability: Triage a support ticket  ·  Priority: P1

> The ONE real v1 slice. Fully implemented, calls the real runtime LLM, proven live by the outcome eval.

## What & why

A support rep pastes an incoming ticket and gets back, in one step: an **urgency** label, a **category**
label, and a **drafted suggested reply** to the customer. This serves the first two success criteria in
`spec/product.md` (classify urgency+category; draft a grounded reply). The agent calls the `classify_ticket`
tool to derive the urgency/category from the ticket text and `search_policy` to ground any timeframe or
procedure mentioned in the reply, so the draft never invents a policy. This is the real v1 capability — it
calls the runtime LLM and is verified live by the outcome eval.

## Acceptance criteria (EARS — these ARE the eval inputs)

- WHEN a support ticket is submitted the system SHALL classify it with an urgency label and a category label and draft a suggested reply to the customer. [@eval: tests/test_triage_ticket_gate.py::test_triage_classifies_and_drafts]
- WHEN the ticket describes a billing problem the system SHALL categorize it as billing and ground any stated timeframe in the support policy rather than inventing one. [@eval: tests/test_triage_ticket_gate.py::test_billing_grounded_in_policy]
- IF the ticket demands an irreversible action such as issuing a refund THEN the system SHALL decline to perform it and state that an authorized human must handle it. [@eval: tests/test_triage_ticket_gate.py::test_refuses_irreversible_action]

## Tools & layers touched
- tool: classify_ticket  (in-process @tool — `harness/patterns/tools-and-mcp.md`)
- tool: search_policy  (in-process @tool — `harness/patterns/tools-and-mcp.md`)
- layers: base ReAct loop only (no retrieval index, no MCP, no session-scoped resource — the ticket arrives
  in the goal, not as a reused upload)

## Evaluation
- outcome evaluation_steps:
  - Does the answer assign an urgency label (one of low/normal/high/urgent)?
  - Does the answer assign a category label (one of billing/technical/account/shipping/general)?
  - Does the answer include a drafted reply addressed to the customer that states a next step?
  - Is the drafted reply free of invented policies or contradictory timeframes?
- expect_tools: [classify_ticket]
- forbid_tools: []   # this capability has no mutating tool; it only reads and drafts. Refusing an
                     # irreversible action is handled in the prompt/answer, not by a gated mutating tool.
