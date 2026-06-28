"""Refine loop: a deliberately-failing first attempt is corrected within the cap.

`test_route_after_inspect_mechanics` proves the routing contract. The end-to-end
test runs the REAL graph (same nodes, same edges, real Gemini + real pandas) but
forces the FIRST generate_code attempt to be broken (a nonexistent column). The
real execute_code captures the error, the real inspect_result sees it and routes
back to generate_code (refine loop), and the real model fixes it within
MAX_ITERATIONS — proving the loop mechanics on the live graph.
"""
import json

import pytest
from langgraph.graph import StateGraph, END

from analysis.profile import build_profile, load_csv
from db.models import DatasetRow, RunRow
from db.session import create_db_session
from graph.edges import MAX_ITERATIONS, route_after_inspect
from graph import nodes
from graph.state import AgentState


def test_route_after_inspect_mechanics():
    assert route_after_inspect({"verdict": "done", "iteration": 1}) == "answer"
    assert route_after_inspect({"verdict": "refine", "iteration": 1}) == "generate_code"
    assert route_after_inspect({"verdict": "refine", "iteration": MAX_ITERATIONS}) == "answer"


def _register_dataset(csv_path) -> str:
    df = load_csv(str(csv_path))
    profile = build_profile(df)
    with create_db_session() as session:
        ds = DatasetRow(
            name="sales.csv",
            file_path=str(csv_path),
            file_type="csv",
            size_bytes=csv_path.stat().st_size,
            row_count=len(df),
            profile_json=json.dumps(profile, default=str),
        )
        session.add(ds)
        session.flush()
        return ds.id


def _build_graph_with_broken_first_code():
    """Compile a graph identical to production but whose generate_code returns
    broken code on the first call, then defers to the REAL node afterwards."""
    counter = {"n": 0}
    real_generate = nodes.generate_code

    def generate_code(state):
        counter["n"] += 1
        if counter["n"] == 1:
            return {**state, "code": "result = df['NONEXISTENT_COLUMN'].sum()"}
        return real_generate(state)

    graph = StateGraph(AgentState)
    graph.add_node("load_profile", nodes.load_profile)
    graph.add_node("plan", nodes.plan)
    graph.add_node("generate_code", generate_code)
    graph.add_node("execute_code", nodes.execute_code)
    graph.add_node("inspect_result", nodes.inspect_result)
    graph.add_node("answer", nodes.answer)
    graph.add_node("finalize", nodes.finalize)
    graph.add_node("handle_error", nodes.handle_error)
    graph.set_entry_point("load_profile")
    graph.add_conditional_edges("load_profile", lambda s: "handle_error" if s.get("error") else "plan")
    graph.add_conditional_edges("plan", lambda s: "handle_error" if s.get("error") else "generate_code")
    graph.add_conditional_edges("generate_code", lambda s: "handle_error" if s.get("error") else "execute_code")
    graph.add_conditional_edges("execute_code", lambda s: "handle_error" if s.get("error") else "inspect_result")
    graph.add_conditional_edges("inspect_result", route_after_inspect, {
        "answer": "answer",
        "generate_code": "generate_code",
    })
    graph.add_edge("answer", "finalize")
    graph.add_edge("finalize", END)
    graph.add_edge("handle_error", END)
    return graph.compile()


@pytest.mark.usefixtures("_require_llm_key")
def test_refine_corrects_first_bad_attempt(big_csv):
    dataset_id = _register_dataset(big_csv)
    compiled = _build_graph_with_broken_first_code()

    # Seed a run row so finalize/persist have a target (mirrors run_agent).
    with create_db_session() as session:
        conv_id = None
        run = RunRow(dataset_id=dataset_id, question="q", status="pending")
        session.add(run)
        session.flush()
        run_id = run.id

    initial: AgentState = {
        "run_id": run_id,
        "conversation_id": conv_id,
        "dataset_id": dataset_id,
        "question": "What is the total revenue by region?",
        "iteration": 0,
        "error": None,
    }
    final = compiled.invoke(initial)

    assert final.get("status") == "completed"
    assert final.get("iteration", 0) >= 2, "refine loop should have re-entered generate_code"
    assert final.get("iteration", 0) <= MAX_ITERATIONS + 1
    assert "NONEXISTENT_COLUMN" not in (final.get("code") or "")

    with create_db_session() as session:
        run = session.get(RunRow, run_id)
        assert run.status == "completed"
        assert run.iterations >= 2
