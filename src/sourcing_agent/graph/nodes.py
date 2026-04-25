from __future__ import annotations

from sourcing_agent.db.models import RecommendationRow, RunRow, SupplierRow
from sourcing_agent.db.session import create_db_session
from sourcing_agent.graph.state import AgentState
from sourcing_agent.tools.enrich import enrich_suppliers
from sourcing_agent.tools.research import research_suppliers
from sourcing_agent.tools.score import score_suppliers


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
        suppliers = enrich_suppliers(
            raw_results=state.get("raw_results", []),
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
