# Vision

## What This Agent Does

The **Lead Gen Agent** discovers small-to-medium businesses (SMBs) across Europe that likely lack an in-house data function, and ranks them as prospects for a data-consulting pitch. Given a country, industry, and employee-size band, it searches the public web, extracts basic firmographics, scores each candidate on likelihood of needing outside data help, and surfaces the ranked list in a web UI with CSV export.

## Who Uses It

A solo data consultant (the operator) preparing a batch of cold-outreach prospects for a week. They need a short, high-signal list — not an exhaustive database — filtered by geography and industry they can credibly serve.

## Core Problem Being Solved

Manually searching LinkedIn / Google / industry directories for SMBs, then guessing which ones lack data maturity, is slow and produces low-signal lists. This agent automates the search, standardizes the firmographic capture, and applies a consistent scoring rubric so the operator spends their time on outreach, not discovery.

## Success Criteria

- [ ] Operator can trigger a run with (country, industry, size-band) and receive ≥10 scored leads within one run
- [ ] Each lead has: name, website, country, industry, size band, HQ city, short description, score (0–100), one-sentence rationale
- [ ] Leads are ranked highest-score-first in the browse UI
- [ ] CSV export of current filtered view works
- [ ] Stub-mode UI is visibly labelled so demo runs are not mistaken for real output

## What This Agent Does NOT Do (Out of Scope for v0.1)

- Deep enrichment (org structure, lines of business, financial data)
- Outreach copy generation
- Paid data providers (Apollo, Clearbit, etc.) — pluggable interface only
- Scheduled / recurring runs
- Multi-user auth
- Non-European geographies

## Key Constraints

- Free public data sources only in v0.1 (DuckDuckGo HTML search)
- Single LLM call per candidate for scoring; must run in stub mode with no API key
- Postgres only (no SQLite, per repo rules)
- Port 8001 for dev

## Phases of Development

| Phase | Description | Success Gate |
|-------|-------------|--------------|
| 1 | Domain models + Postgres schema via Alembic | `uv run alembic upgrade head` + repository CRUD tests pass |
| 2 | Stubbed agent loop (search → extract → score → persist) + FastAPI/Jinja UI + CSV export | `uv run pytest` all green with no `GEMINI_API_KEY`; golden-path UI smoke + live-server curl both pass |
| 3 | Real Gemini integration for scoring; real DuckDuckGo search | End-to-end run against live services produces ≥10 leads |
| 4 | Error resilience + structured logging | Agent survives network failure, search timeouts, LLM 4xx/5xx |
| 5 (future) | Enrichment (financials, LOBs) | |
| 6 (future) | Outreach copy generation | |
