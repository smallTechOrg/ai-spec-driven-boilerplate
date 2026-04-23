---
description: "Dispatch the planner agent to draft a phase-wise gated plan in reports/ for the described task. Planning comes before code."
agent: agent
argument-hint: "[one-line task description]"
tools: [read, search, edit]
---

Use the `planner` agent to run the workflow defined
in [`spec/engineering/workflows/plan.md`](../../spec/engineering/workflows/plan.md) for this task:
$ARGUMENTS.

Return the path to the written plan and a 3-bullet summary.
