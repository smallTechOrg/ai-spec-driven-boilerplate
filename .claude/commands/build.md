# /build

Kick off the agent-builder with your zero-shot idea.

## Usage

```
/build [your idea]
```

## Examples

```
/build An agent that monitors my GitHub repos for open PRs older than 3 days and sends Slack reminders
```

```
/build A daily digest agent that pulls from my RSS feeds, summarizes with Claude, and emails me at 8am
```

```
/build An agent that watches my Shopify store for low inventory and auto-drafts restock emails to suppliers — use Python and FastAPI
```

## What Happens

The agent-builder sub-agent takes your idea and runs the full lifecycle:
1. Asks clarifying questions until requirements are clear
2. Spec-writer drafts the product spec; you approve
3. Tech-designer proposes the stack; you approve
4. Planner creates a phased build plan; you approve
5. Builds phase by phase, with QA gates between each phase
6. Drift audit at the end
7. Hands off a working agent

You are consulted at each approval gate. Nothing proceeds without your sign-off.

## Arguments

The text after `/build` is your idea. The more detail you give, the fewer clarifying questions you'll be asked. You can include:
- What the agent does
- Who uses it
- What integrations it needs
- Tech preferences (language, framework, etc.)
- Constraints (budget, latency, compliance)

## Invocation

This command invokes `.claude/agents/agent-builder.md`. The agent-builder will guide you through the rest.
