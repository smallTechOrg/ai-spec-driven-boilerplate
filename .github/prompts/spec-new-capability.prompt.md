---
description: "Scaffold a new capability spec file in spec/product/capabilities/ using the standard template."
agent: agent
argument-hint: "[capability-slug]"
tools: [read, search, edit]
---

Run the workflow defined
in [`spec/engineering/workflows/spec-new-capability.md`](../../spec/engineering/workflows/spec-new-capability.md).

If the user passed a slug argument, treat it as the capability slug: $ARGUMENTS.
