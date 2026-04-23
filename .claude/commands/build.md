# /build

Kick off the agent-builder with your zero-shot idea. One prompt → working skeleton.

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
/build An agent that watches my Shopify store for low inventory and auto-drafts restock emails — Python, PostgreSQL, deploy to Railway
```

## The more detail you give, the faster it goes

Include in your prompt:
- What the agent does
- Tech preferences: language, database, hosting (e.g. "Python, PostgreSQL")
- Key integrations or API keys you have
- Any hard constraints

The agent-builder asks **4 questions upfront** (scope, stack, output/trigger, constraints), then produces spec + tech design + build plan in one shot. You approve once, then it builds.

## What Happens

```
Your prompt
    ↓
4 intake questions (scope, stack, trigger, constraints)
    ↓
Spec + tech design + v0.1 plan drafted together
    ↓
One summary → you approve once
    ↓
Phase 1: domain models + DB schema (tests pass)
    ↓
Phase 2: stubbed agent loop end-to-end (tests pass)
    ↓
Skeleton is running — iterate from here
```

**Target: working skeleton in ~10 minutes.**

## Invocation

This command invokes `.claude/agents/agent-builder.md`.
