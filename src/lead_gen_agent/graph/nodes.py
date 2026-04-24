"""LangGraph nodes: search → extract → score → persist.

Every LLM prompt carries an unambiguous `<node:*>` tag; the stub branches on those
tags only (never on prose keywords — repo rule 8).
"""
from __future__ import annotations

import json
import logging

from lead_gen_agent.config.settings import get_settings
from lead_gen_agent.db import repository as repo
from lead_gen_agent.db.session import create_db_session
from lead_gen_agent.domain.models import Candidate, Lead
from lead_gen_agent.graph.state import AgentState
from lead_gen_agent.llm.client import get_llm_client
from lead_gen_agent.tools.search import get_search_tool

log = logging.getLogger(__name__)


def _stub_mode() -> bool:
    return get_settings().resolved_llm_provider == "stub"


def search_node(state: AgentState) -> AgentState:
    try:
        tool = get_search_tool(stub=_stub_mode())
        query = f"{state['country']} {state['industry']} company {state['size_band']} employees"
        results = tool.search(query, limit=10)
        return {**state, "search_results": results}
    except Exception as e:  # defensive — rule 8 (error resilience)
        log.exception("search_node failed")
        return {**state, "error": f"search: {e}", "search_results": []}


def extract_node(state: AgentState) -> AgentState:
    results = state.get("search_results") or []
    if not results:
        return {**state, "candidates": []}
    prompt = (
        "<node:extract>\n"
        "You are extracting firmographics for lead-gen. For each search hit below, "
        "produce a JSON array of objects with fields: name, website, hq_city, description.\n"
        f"country={state['country']}, industry={state['industry']}, size_band={state['size_band']}\n\n"
        + json.dumps(results)
    )
    try:
        raw = get_llm_client().complete(prompt)
        records = json.loads(raw)
        candidates = [
            Candidate(
                name=r.get("name", "Unknown"),
                website=r.get("website"),
                country=state["country"],
                industry=state["industry"],
                size_band=state["size_band"],
                hq_city=r.get("hq_city"),
                description=r.get("description"),
            )
            for r in records
            if r.get("name")
        ]
        return {**state, "candidates": candidates}
    except Exception as e:
        log.exception("extract_node failed")
        return {**state, "error": f"extract: {e}", "candidates": []}


def score_node(state: AgentState) -> AgentState:
    candidates = state.get("candidates") or []
    if not candidates:
        return {**state, "leads": []}
    client = get_llm_client()
    leads: list[Lead] = []
    for c in candidates:
        prompt = (
            "<node:score>\n"
            "Score 0-100 the likelihood this company LACKS an in-house data function. "
            "Signals: small size, traditional industry, thin tech stack, no data-role job postings.\n"
            "Return strict JSON: {\"score\": <int>, \"rationale\": \"<one sentence>\"}.\n\n"
            f"name={c.name}\nindustry={c.industry}\nsize_band={c.size_band}\n"
            f"hq_city={c.hq_city}\ndescription={c.description}\n"
        )
        try:
            raw = client.complete(prompt)
            obj = json.loads(raw)
            score = int(obj.get("score", 50))
            score = max(0, min(100, score))
            rationale = str(obj.get("rationale") or "")[:400]
        except Exception:
            log.exception("score parse failed for %s", c.name)
            score, rationale = 50, "score unparseable — manual review"
        leads.append(Lead(**c.model_dump(), score=score, rationale=rationale))
    return {**state, "leads": leads}


def persist_node(state: AgentState) -> AgentState:
    run_id = state["run_id"]
    try:
        with create_db_session() as s:
            for lead in state.get("leads") or []:
                repo.add_lead(s, run_id, lead)
            status = "failed" if state.get("error") else "completed"
            repo.complete_run(s, run_id, status, error=state.get("error"))
        return {**state, "status": status}
    except Exception as e:
        log.exception("persist_node failed")
        with create_db_session() as s:
            repo.complete_run(s, run_id, "failed", error=f"persist: {e}")
        return {**state, "status": "failed", "error": f"persist: {e}"}
