# Product

> Filled by the **spec-writer** from intake. Part 1 of the 4-part spec contract (see `harness/harness.md`).
> This file is the **intent of record** for the domain: the spec is truth here. Every success criterion below
> maps to **≥1 capability** in `spec/capabilities/`; the analyze pre-flight fails the build if any criterion
> has no capability.

## What it does

A customer-support triage agent. A support rep (or an inbox automation) pastes in an incoming support
ticket — the customer's message, optionally with a subject line — and the agent reads it, decides **how
urgent** it is and **what category** it belongs to, and **drafts a suggested reply** the rep can send or
edit. It turns a raw, unsorted ticket into a triaged, ready-to-action item in one step, so the support
queue is sorted by urgency and every ticket arrives with a first-draft response already written. The
person using it is a support agent or team lead who wants the routing decision and the reply draft made
for them, grounded in the company's actual support policies rather than invented.

## Success criteria (these feed the outcome eval — keep them testable)

- [x] Given a ticket, the agent returns an **urgency** (`low` / `normal` / `high` / `urgent`) and a
  **category** (e.g. billing, technical, account, shipping, general) for it. (→ triage-ticket)
- [x] The agent **drafts a suggested reply** addressed to the customer that acknowledges the issue and
  states the next step, grounded in the support policy corpus rather than invented facts. (→ triage-ticket)
- [x] A high/urgent ticket can be **escalated** to a human queue with a routing reason. (→ escalate-ticket)
- [x] A long back-and-forth ticket thread can be **summarized** to its open question. (→ summarize-thread)

## Domain instructions (the agent's system-prompt guidance for this domain)

You are a customer-support triage assistant. For an incoming ticket you: (1) classify its **urgency** as one
of `low`, `normal`, `high`, `urgent`, and its **category** as one of `billing`, `technical`, `account`,
`shipping`, `general`; (2) draft a short, professional **suggested reply** to the customer that acknowledges
their problem and states the concrete next step. Always call the `classify_ticket` tool to obtain the
urgency/category rather than guessing, and consult `search_policy` for the relevant support policy before
stating any timeframe or procedure in the reply — never invent a policy or a number. Keep the reply concise,
empathetic, and free of internal jargon. Present the result as the urgency, the category, then the drafted
reply. If a request asks you to take an irreversible action (issue a refund, delete an account, charge a
card), do not perform it — say it must be handled by an authorized human and draft the reply accordingly.

## Out of scope (Future Phases)

- Actually sending the reply, issuing refunds, or mutating any customer record (the agent only drafts).
- Connecting to a live helpdesk (Zendesk/Intercom) inbox — tickets arrive as pasted text in v1.
- Multi-language detection/translation.
- The escalate-ticket and summarize-thread capabilities ship in v1 as deterministic, journey-complete
  **stubs** (registered and reachable, returning a fixed contract); they are promoted to real
  implementations in a follow-up build via `/spec-new-capability`.
