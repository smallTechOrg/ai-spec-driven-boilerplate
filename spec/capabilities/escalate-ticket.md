# Capability: Escalate a ticket to a human queue  ·  Priority: P2

> A deterministic, journey-complete, spec-registered **STUB**. Wired into the graph and reachable end-to-end,
> but returns a fixed contract instead of doing the real routing. Promoted to a real implementation in a
> follow-up build via `/spec-new-capability`.

## What & why

When a ticket is high/urgent, a rep should be able to escalate it to a named human queue with a routing
reason. Serves the "a high/urgent ticket can be escalated" success criterion in `spec/product.md`. **Stub
contract until promoted:** the `escalate_ticket` tool returns a fixed, well-formed escalation record —
`{"queue": "tier-2", "status": "escalated", "reason": <echoed>}` — so the journey is complete and the
capability is registered, even though no real queue/router is wired yet.

## Acceptance criteria (EARS — these ARE the eval inputs)

- WHEN a ticket is escalated the system SHALL return an escalation record naming the target queue and status escalated. [@eval: tests/test_escalate_ticket_gate.py::test_escalation_returns_queue_record]

## Tools & layers touched
- tool: escalate_ticket  (in-process @tool, STUB — `harness/patterns/tools-and-mcp.md`)
- layers: base ReAct loop only

## Evaluation
- outcome evaluation_steps:
  - Does the escalation record name a target queue?
  - Is the status "escalated"?
- expect_tools: [escalate_ticket]
- forbid_tools: []   # the stub is non-mutating; it returns a fixed record.
