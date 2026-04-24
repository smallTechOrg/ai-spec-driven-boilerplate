"""Graph node functions: (AgentState) → AgentState."""
from __future__ import annotations

import json
import logging

from lead_gen_agent.domain import Contact, LeadCreate
from lead_gen_agent.graph.progress import emit
from lead_gen_agent.graph.state import AgentState
from lead_gen_agent.llm import create_llm_provider

logger = logging.getLogger(__name__)


def search_node(state: AgentState) -> AgentState:
    """Discover EU SMBs matching the search criteria."""
    criteria = state["criteria"]
    run_id = state["run_id"]
    size_clause = ""
    if criteria.size_min or criteria.size_max:
        size_clause = (
            f" with between {criteria.size_min or 1} and {criteria.size_max or '∞'} employees"
        )

    emit(run_id, "search", f"Searching for {criteria.industry} companies in {criteria.country}{size_clause}…")

    prompt = (
        f"<node:search>\n"
        f"Find 5 real small-to-medium businesses in {criteria.country} "
        f"in the {criteria.industry} sector{size_clause}. "
        f"These businesses should NOT have an in-house data / analytics team. "
        f"Return a JSON array (no markdown, no extra text) with objects: "
        f'[{{"name": "...", "domain": "...", "website": "..."}}]'
    )
    try:
        llm = create_llm_provider()
        raw = llm.generate(prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        companies = json.loads(raw)
        emit(run_id, "search", f"✓ Found {len(companies)} companies")
        return {**state, "raw_companies": companies}
    except Exception as exc:
        logger.error("search_node failed: %s", exc)
        emit(run_id, "search", f"✗ Search failed: {exc}")
        return {**state, "error": f"search_node: {exc}"}


def enrich_node(state: AgentState) -> AgentState:
    """Enrich each discovered company with firmographic details."""
    run_id = state["run_id"]
    criteria = state["criteria"]
    companies = state.get("raw_companies", [])
    llm = create_llm_provider()
    leads: list[LeadCreate] = []

    emit(run_id, "enrich", f"Enriching {len(companies)} companies…")

    for company in companies:
        name = company.get("name", "Unknown")
        domain = company.get("domain", "")
        website = company.get("website", "")
        if not domain:
            continue
        emit(run_id, "enrich", f"  Enriching {name}…")
        prompt = (
            f"<node:enrich>\n"
            f"Company: {name} ({domain})\n"
            f"Country: {criteria.country}\n"
            f"Return a JSON object (no markdown) with:\n"
            f'{{"industry": "...", "headcount_estimate": "...", '
            f'"why_fit": "2 sentences on why this company is a good data consultancy target"}}'
        )
        try:
            raw = llm.generate(prompt)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            enrichment = json.loads(raw)
        except Exception as exc:
            logger.warning("enrich_node skipping %s: %s", name, exc)
            enrichment = {}

        leads.append(LeadCreate(
            search_run_id=run_id,
            company_name=name,
            domain=domain,
            website=website,
            country=criteria.country,
            industry=enrichment.get("industry", criteria.industry),
            headcount_estimate=enrichment.get("headcount_estimate"),
            why_fit=enrichment.get("why_fit"),
        ))

    emit(run_id, "enrich", f"✓ Enriched {len(leads)} leads")
    return {**state, "leads": leads}


def contact_node(state: AgentState) -> AgentState:
    """Find publicly-available business contacts for each enriched lead."""
    run_id = state["run_id"]
    leads = state.get("leads", [])
    llm = create_llm_provider()
    enriched: list[LeadCreate] = []

    emit(run_id, "contacts", f"Finding contacts for {len(leads)} companies…")

    for lead in leads:
        emit(run_id, "contacts", f"  Looking up contacts for {lead.company_name}…")
        prompt = (
            f"<node:contact>\n"
            f"Company: {lead.company_name} ({lead.domain})\n"
            f"Country: {lead.country}\n"
            f"Find up to 3 publicly-discoverable business contacts at this company "
            f"(decision-makers, data leads, tech leads). "
            f"Only include contacts findable via public sources: company website, LinkedIn public profiles, "
            f"press releases. Do NOT guess or infer personal details.\n"
            f"Return a JSON array (no markdown):\n"
            f'[{{"name": "...", "title": "...", "email": "...", "phone": "...", "linkedin_url": "..."}}]\n'
            f"Use null for any field that is not publicly available."
        )
        try:
            raw = llm.generate(prompt)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            contacts_raw = json.loads(raw)
            contacts = [Contact(**c) for c in contacts_raw if isinstance(c, dict)]
        except Exception as exc:
            logger.warning("contact_node skipping %s: %s", lead.company_name, exc)
            contacts = []

        enriched.append(lead.model_copy(update={"contacts": contacts}))

    found = sum(len(l.contacts) for l in enriched)
    emit(run_id, "contacts", f"✓ Found {found} contacts across {len(enriched)} companies")
    return {**state, "leads": enriched}


def save_node(state: AgentState) -> AgentState:
    """Upsert leads and mark the run completed."""
    from lead_gen_agent.db import create_db_session
    from lead_gen_agent.db.repository import LeadRepository, SearchRunRepository

    run_id = state["run_id"]
    leads = state.get("leads", [])
    emit(run_id, "save", f"Saving {len(leads)} leads to database…")
    try:
        with create_db_session() as session:
            lead_repo = LeadRepository(session)
            run_repo = SearchRunRepository(session)
            count = lead_repo.upsert_many(leads)
            run_repo.mark_completed(run_id, lead_count=count)
        emit(run_id, "save", f"✓ {count} leads saved — run complete")
    except Exception as exc:
        logger.error("save_node failed: %s", exc)
        emit(run_id, "save", f"✗ Save failed: {exc}")
        return {**state, "error": f"save_node: {exc}"}
    return state


def handle_error(state: AgentState) -> AgentState:
    """Persist the error and mark the run failed."""
    from lead_gen_agent.db import create_db_session
    from lead_gen_agent.db.repository import SearchRunRepository

    run_id = state["run_id"]
    error_msg = state.get("error") or "Unknown error"
    emit(run_id, "error", f"✗ Run failed: {error_msg}")
    try:
        with create_db_session() as session:
            SearchRunRepository(session).mark_failed(run_id, error_msg)
    except Exception as exc:
        logger.error("handle_error could not update run: %s", exc)
    return state



def search_node(state: AgentState) -> AgentState:
    """Discover EU SMBs matching the search criteria."""
    criteria = state["criteria"]
    size_clause = ""
    if criteria.size_min or criteria.size_max:
        size_clause = (
            f" with between {criteria.size_min or 1} and {criteria.size_max or '∞'} employees"
        )

    prompt = (
        f"<node:search>\n"
        f"Find 5 real small-to-medium businesses in {criteria.country} "
        f"in the {criteria.industry} sector{size_clause}. "
        f"These businesses should NOT have an in-house data / analytics team. "
        f"Return a JSON array (no markdown, no extra text) with objects: "
        f'[{{"name": "...", "domain": "...", "website": "..."}}]'
    )
    try:
        llm = create_llm_provider()
        raw = llm.generate(prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        companies = json.loads(raw)
        return {**state, "raw_companies": companies}
    except Exception as exc:
        logger.error("search_node failed: %s", exc)
        return {**state, "error": f"search_node: {exc}"}


def enrich_node(state: AgentState) -> AgentState:
    """Enrich each discovered company with firmographic details."""
    run_id = state["run_id"]
    criteria = state["criteria"]
    companies = state.get("raw_companies", [])
    llm = create_llm_provider()
    leads: list[LeadCreate] = []

    for company in companies:
        name = company.get("name", "Unknown")
        domain = company.get("domain", "")
        website = company.get("website", "")
        if not domain:
            continue
        prompt = (
            f"<node:enrich>\n"
            f"Company: {name} ({domain})\n"
            f"Country: {criteria.country}\n"
            f"Return a JSON object (no markdown) with:\n"
            f'{{"industry": "...", "headcount_estimate": "...", '
            f'"why_fit": "2 sentences on why this company is a good data consultancy target"}}'
        )
        try:
            raw = llm.generate(prompt)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            enrichment = json.loads(raw)
        except Exception as exc:
            logger.warning("enrich_node skipping %s: %s", name, exc)
            enrichment = {}

        leads.append(LeadCreate(
            search_run_id=run_id,
            company_name=name,
            domain=domain,
            website=website,
            country=criteria.country,
            industry=enrichment.get("industry", criteria.industry),
            headcount_estimate=enrichment.get("headcount_estimate"),
            why_fit=enrichment.get("why_fit"),
        ))

    return {**state, "leads": leads}


def save_node(state: AgentState) -> AgentState:
    """Upsert leads and mark the run completed."""
    from lead_gen_agent.db import create_db_session
    from lead_gen_agent.db.repository import LeadRepository, SearchRunRepository

    run_id = state["run_id"]
    leads = state.get("leads", [])
    try:
        with create_db_session() as session:
            lead_repo = LeadRepository(session)
            run_repo = SearchRunRepository(session)
            count = lead_repo.upsert_many(leads)
            run_repo.mark_completed(run_id, lead_count=count)
    except Exception as exc:
        logger.error("save_node failed: %s", exc)
        return {**state, "error": f"save_node: {exc}"}
    return state


def handle_error(state: AgentState) -> AgentState:
    """Persist the error and mark the run failed."""
    from lead_gen_agent.db import create_db_session
    from lead_gen_agent.db.repository import SearchRunRepository

    run_id = state["run_id"]
    error_msg = state.get("error") or "Unknown error"
    try:
        with create_db_session() as session:
            SearchRunRepository(session).mark_failed(run_id, error_msg)
    except Exception as exc:
        logger.error("handle_error could not update run: %s", exc)
    return state
