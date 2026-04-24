# Vision

## What This Agent Does

The EU Lead Gen Agent helps a solo data consultant discover and prioritise small-to-medium European businesses that lack an in-house data function — making them strong candidates for a data consultancy pitch. Given search criteria (country, industry, headcount range), the agent uses Gemini with Google Search Grounding to find matching companies, enriches each with firmographic data, stores leads in a PostgreSQL database, and surfaces them in a web dashboard with CSV export.

## Who Uses It

A freelance or independent data consultant operating in Europe. The user wants a steady pipeline of warm, well-researched outreach targets without spending hours manually searching LinkedIn or company databases.

## Core Problem Being Solved

Identifying SMBs that are big enough to benefit from data work but small enough to not already have a data team requires combining public signals across many sources. Today this is done manually and inconsistently. The agent automates discovery and enrichment so the consultant can focus on personalised outreach rather than prospecting.

## Success Criteria

- [ ] Given search criteria, the agent discovers ≥ 5 relevant EU SMB leads per run
- [ ] Each lead includes: company name, website, country, industry, estimated headcount, and a 2-sentence "why they fit" summary
- [ ] Leads are stored in PostgreSQL with deduplication (no duplicate domains)
- [ ] Dashboard lets the user browse, filter, and export leads to CSV in < 3 clicks
- [ ] Stub mode runs offline without any API key; live mode requires only the Gemini API key

## What This Agent Does NOT Do (Out of Scope)

- Does not generate personalised outreach copy (Phase 5)
- Does not pull org charts or deep financial data (Phase 5)
- Does not integrate with a CRM or email sequencer (Phase 5+)
- Does not cover non-European markets

## Key Constraints

- Gemini API rate limits apply (60 requests/minute free tier); the agent must not exceed this
- Contact data stored is **publicly discoverable business contacts only** (company website bios, LinkedIn public profiles, press releases). The LLM prompt must not ask the model to infer or guess personal contact details. This keeps the feature within GDPR legitimate-interest grounds for B2B prospecting.
- Must run locally; no cloud deployment required in v0.1

## Phases of Development

| Phase | Description | Success Gate |
|-------|-------------|--------------|
| 1 | Domain models + DB schema (Lead, SearchRun) + repository CRUD | `uv run pytest tests/unit/ -q` 100% green against PostgreSQL |
| 2 | LangGraph pipeline (search → enrich nodes, stubbed) + FastAPI web UI + CSV export + README | `uv run pytest -q` + golden-path smoke test green; app starts and serves real pages |
| 3 | Contact enrichment node (publicly-available contacts per lead) + SSE observability (live progress feed during runs) | Pipeline produces contacts per lead; run page streams live progress via SSE |
| 4 | Replace stubs with live Gemini + Google Search Grounding calls | End-to-end run produces real leads + contacts; gate: ≥ 5 leads stored per run |
| 5 | Outreach copy generation per lead | Each lead has AI-drafted intro paragraph |
