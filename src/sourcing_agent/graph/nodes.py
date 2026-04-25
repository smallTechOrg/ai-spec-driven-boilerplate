"""LangGraph node functions — each takes AgentState and returns a partial state update."""

import json
import logging
import uuid
from decimal import Decimal

from sourcing_agent.db.repository import (
    get_run_with_details,
    save_recommendations,
    update_run_status,
)
from sourcing_agent.db.session import get_session
from sourcing_agent.domain.models import SourcingRunStatus, SupplierCandidateData
from sourcing_agent.graph.state import AgentState
from sourcing_agent.llm import get_llm_client

logger = logging.getLogger(__name__)


def intake_node(state: AgentState) -> dict:
    """Load run and materials from DB; set status=running."""
    run_id = uuid.UUID(state["run_id"])
    try:
        with get_session() as session:
            run = get_run_with_details(session, run_id)
            if run is None:
                return {"status": SourcingRunStatus.FAILED, "error": f"Run {run_id} not found"}
            update_run_status(session, run_id, SourcingRunStatus.RUNNING)
            materials = [
                {"name": item.material_name, "quantity": float(item.quantity), "unit": item.unit}
                for item in run.line_items
            ]
            project_name = run.project_name
        return {
            "project_name": project_name,
            "materials": materials,
            "supplier_candidates": {},
            "recommendations": {},
            "status": SourcingRunStatus.RUNNING,
            "error": None,
        }
    except Exception as exc:
        logger.exception("intake_node failed: %s", exc)
        return {"status": SourcingRunStatus.FAILED, "error": str(exc)}


def research_node(state: AgentState) -> dict:
    """Call LLM to discover suppliers for each material."""
    if state.get("status") == SourcingRunStatus.FAILED:
        return {}

    client = get_llm_client()
    all_candidates: dict[str, list[dict]] = {}

    for material in state["materials"]:
        name = material["name"]
        qty = material["quantity"]
        unit = material["unit"]

        prompt = (
            f"<node:research>\n"
            f"You are a construction materials procurement specialist.\n"
            f"Find 3 realistic supplier options for: {qty} {unit} of {name}.\n"
            f"Return a JSON array (no markdown) where each item has:\n"
            f"  supplier_name, supplier_location, price_per_unit, currency, "
            f"lead_time_days, certifications (array), notes.\n"
            f"Return ONLY the JSON array, no other text."
        )

        try:
            raw = client.generate(prompt)
            # Strip markdown code fences if present
            clean = raw.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                clean = "\n".join(lines[1:-1]) if len(lines) > 2 else clean
            candidates = json.loads(clean)
            if not isinstance(candidates, list):
                candidates = []
        except Exception as exc:
            logger.warning("research_node failed for %s: %s", name, exc)
            candidates = []

        all_candidates[name] = candidates

    return {"supplier_candidates": all_candidates}


def rank_node(state: AgentState) -> dict:
    """Score and rank candidates; persist recommendations to DB."""
    if state.get("status") == SourcingRunStatus.FAILED:
        return {}

    from sourcing_agent.config.settings import get_settings

    settings = get_settings()
    w_price = settings.weight_price
    w_lead = settings.weight_lead_time
    w_certs = settings.weight_certs

    run_id = uuid.UUID(state["run_id"])
    all_recommendations: dict[str, list[dict]] = {}

    with get_session() as session:
        from sourcing_agent.db.models import MaterialLineItem
        from sqlalchemy import select

        stmt = select(MaterialLineItem).where(MaterialLineItem.run_id == run_id)
        line_items = session.execute(stmt).scalars().all()
        item_map = {item.material_name: item for item in line_items}

        for material in state["materials"]:
            name = material["name"]
            raw_candidates = state["supplier_candidates"].get(name, [])
            if not raw_candidates:
                all_recommendations[name] = []
                continue

            # Normalise prices and lead times across candidates for this material
            prices = [float(c.get("price_per_unit", 0) or 0) for c in raw_candidates]
            leads = [int(c.get("lead_time_days", 0) or 0) for c in raw_candidates]
            min_p, max_p = min(prices), max(prices)
            min_l, max_l = min(leads), max(leads)
            p_range = (max_p - min_p) or 1.0
            l_range = (max_l - min_l) or 1.0

            candidates_with_scores: list[SupplierCandidateData] = []
            for raw in raw_candidates:
                price = float(raw.get("price_per_unit", 0) or 0)
                lead = int(raw.get("lead_time_days", 0) or 0)
                certs = raw.get("certifications") or []
                if isinstance(certs, str):
                    certs = [c.strip() for c in certs.split(",") if c.strip()]

                norm_price = (price - min_p) / p_range
                norm_lead = (lead - min_l) / l_range
                cert_score = min(1.0, len(certs) / 3)
                score = (1 - norm_price) * w_price + (1 - norm_lead) * w_lead + cert_score * w_certs

                candidates_with_scores.append(
                    SupplierCandidateData(
                        supplier_name=raw.get("supplier_name", "Unknown"),
                        supplier_location=raw.get("supplier_location"),
                        price_per_unit=price,
                        currency=raw.get("currency", "USD"),
                        lead_time_days=lead,
                        certifications=certs,
                        notes=raw.get("notes"),
                        score=round(score, 4),
                    )
                )

            # Sort descending by score (best first)
            candidates_with_scores.sort(key=lambda c: c.score, reverse=True)

            line_item = item_map.get(name)
            if line_item is not None:
                save_recommendations(session, run_id, line_item.id, candidates_with_scores)

            all_recommendations[name] = [c.model_dump() for c in candidates_with_scores]

        update_run_status(session, run_id, SourcingRunStatus.COMPLETED)

    return {"recommendations": all_recommendations, "status": SourcingRunStatus.COMPLETED}


def error_handler_node(state: AgentState) -> dict:
    """Persist failed status to DB."""
    run_id_str = state.get("run_id")
    error = state.get("error", "Unknown error")
    if run_id_str:
        try:
            run_id = uuid.UUID(run_id_str)
            with get_session() as session:
                update_run_status(session, run_id, SourcingRunStatus.FAILED, error_message=error)
        except Exception:
            pass
    return {}
