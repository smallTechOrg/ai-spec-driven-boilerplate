from __future__ import annotations

from sourcing_agent.db.models import RecommendationRow, RunRow, SupplierRow
from sourcing_agent.db.session import create_db_session
from sourcing_agent.graph.state import AgentState
from sourcing_agent.tools.enrich import enrich_suppliers
from sourcing_agent.tools.research import research_suppliers
from sourcing_agent.tools.score import score_suppliers
from sourcing_agent.tools.signals import attach_signals_to_results


def _to_float(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _to_int(v):
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _to_bool(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    if isinstance(v, str):
        return v.strip().lower() in ("true", "yes", "1")
    return bool(v)


def research(state: AgentState) -> AgentState:
    try:
        req = state["request"]
        results = research_suppliers(
            material=req["material"],
            location=req["location"],
        )
        return {**state, "raw_results": results}
    except Exception as e:  # noqa: BLE001
        return {**state, "error": f"research failed: {e}"}


def enrich(state: AgentState) -> AgentState:
    try:
        req = state["request"]
        results_with_signals = attach_signals_to_results(
            state.get("raw_results", []), req["location"]
        )
        suppliers = enrich_suppliers(
            raw_results=results_with_signals,
            material=req["material"],
            location=req["location"],
        )
        with create_db_session() as session:
            persisted: list[dict] = []
            for s in suppliers:
                row = SupplierRow(
                    run_id=state["run_id"],
                    name=s.get("name") or "Unknown",
                    location=s.get("location"),
                    price_indication=s.get("price_indication"),
                    lead_time=s.get("lead_time"),
                    source_url=s.get("source_url"),
                    notes=s.get("notes"),
                    google_rating=_to_float(s.get("google_rating")),
                    google_review_count=_to_int(s.get("google_review_count")),
                    feedback_summary=s.get("feedback_summary"),
                    delivery_reliability=s.get("delivery_reliability"),
                    years_in_business=_to_int(s.get("years_in_business")),
                    solvency_signal=s.get("solvency_signal"),
                    gst_registered=_to_bool(s.get("gst_registered")),
                )
                session.add(row)
                session.flush()
                persisted.append({**s, "id": row.id})
        return {**state, "suppliers": persisted}
    except Exception as e:  # noqa: BLE001
        return {**state, "error": f"enrich failed: {e}"}


def score(state: AgentState) -> AgentState:
    try:
        req = state["request"]
        ranked = score_suppliers(
            suppliers=state.get("suppliers", []),
            material=req["material"],
            location=req["location"],
            quantity=req["quantity"],
            budget=req.get("budget"),
            timeline=req.get("timeline"),
            criteria=req.get("criteria"),
        )

        # Map supplier name → id from state
        name_to_id = {s.get("name"): s.get("id") for s in state.get("suppliers", [])}
        with create_db_session() as session:
            persisted: list[dict] = []
            for rank, item in enumerate(ranked, start=1):
                supplier_id = name_to_id.get(item.get("supplier_name"))
                if not supplier_id:
                    continue
                row = RecommendationRow(
                    run_id=state["run_id"],
                    supplier_id=supplier_id,
                    rank=rank,
                    score=int(item.get("score", 0)),
                    rationale=item.get("rationale", ""),
                )
                session.add(row)
                session.flush()
                persisted.append(
                    {
                        "id": row.id,
                        "supplier_id": supplier_id,
                        "rank": rank,
                        "score": row.score,
                        "rationale": row.rationale,
                    }
                )
        return {**state, "recommendations": persisted}
    except Exception as e:  # noqa: BLE001
        return {**state, "error": f"score failed: {e}"}


def finalize(state: AgentState) -> AgentState:
    with create_db_session() as session:
        run = session.get(RunRow, state["run_id"])
        if run is not None:
            run.status = "completed"
    return state


def handle_error(state: AgentState) -> AgentState:
    with create_db_session() as session:
        run = session.get(RunRow, state["run_id"])
        if run is not None:
            run.status = "failed"
            run.error_message = state.get("error") or "unknown error"
    return state
