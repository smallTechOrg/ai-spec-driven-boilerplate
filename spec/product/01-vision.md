# Vision

## What This Agent Does

The Sourcing Agent for Construction Materials automates supplier discovery and comparison for real estate construction projects. Given a list of materials and quantities, it researches candidate suppliers, compares them on price, lead time, and quality certifications, and produces a ranked recommendation report — replacing hours of manual procurement research.

## Who Uses It

Procurement managers and project managers at real estate development and construction companies who need to source materials (bricks, cement, steel, sand, timber, etc.) for upcoming projects.

## Core Problem Being Solved

Manually sourcing construction materials requires contacting dozens of suppliers, collating quotes in spreadsheets, and subjectively comparing options. This agent automates discovery and ranking so a manager can get actionable recommendations in minutes instead of days.

## Success Criteria

- [ ] User submits a project with a materials list via web form and receives a ranked supplier report within 60 seconds (stub) or 5 minutes (real)
- [ ] Each material line shows at least 3 ranked supplier options with price, lead time, and certification data
- [ ] Recommendations are ranked by a weighted score across price, lead time, and quality certifications
- [ ] Agent run status is persisted in PostgreSQL; user can revisit completed reports
- [ ] All tests pass without a real LLM API key (stub mode)

## What This Agent Does NOT Do (Out of Scope)

- Does not generate or send RFQs or purchase orders
- Does not integrate with live pricing APIs (future phase)
- Does not manage supplier relationships or a supplier CRM
- Does not support multi-user authentication in v0.1
- Does not schedule or automate recurring sourcing runs

## Key Constraints

- LLM: Google Gemini (`gemini-2.0-flash` model)
- Database: PostgreSQL
- Web UI required (Jinja2 + FastAPI)
- Recommendations must cite criteria: price, lead time, ISO certifications
- Stub mode must show a visible banner; never simulate real output silently

## Phases of Development

| Phase | Description | Success Gate |
|-------|-------------|--------------|
| 1 | Domain models + PostgreSQL schema + CRUD repository | `uv run pytest tests/unit/` passes 100% against PostgreSQL |
| 2 | Stubbed agent loop + FastAPI + Jinja2 UI | `uv run pytest` passes; golden-path smoke test green; live server returns 200 |
| 3 | Real Gemini integration for supplier research | Agent runs with real Gemini API; report contains real supplier data |
| 4 | Error handling + resilience | All failure modes handled without crash |

## Future Phases

- Real-time pricing API integrations (e.g., material exchange APIs)
- RFQ generation and email dispatch to suppliers
- Supplier CRM / database
- Multi-user authentication
- Scheduled / recurring sourcing runs
- Export to PDF / Excel
