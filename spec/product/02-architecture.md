# Architecture

## System Overview
Single Python process, CLI-invoked. LangGraph pipeline: fetch → classify/draft (per email, parallel) → persist. SQLite for results.

## Component Map
```
[CLI: python -m emailtriage run]
        │
[LangGraph Agent]
   fetch_emails → classify_and_draft → persist_results → finalize
        │
   [Gmail API]  [Claude API]  [SQLite]
```

## External Dependencies
| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Gmail API | Fetch emails | Fatal — mark run failed |
| Claude API | Classify + draft | Per-email — mark that email as error, continue |
| SQLite | Persist results | Log error, continue |
