from langgraph.graph import END, StateGraph

from blogforge.agent.nodes import (
    node_finalize,
    node_handle_error,
    node_image_generation,
    node_post_generation,
    node_topic_discovery,
    node_writer_assignment,
)
from blogforge.agent.state import GenerationState


def _route_after_discovery(state: GenerationState) -> str:
    return "node_handle_error" if state.get("error") else "node_writer_assignment"


def _route_after_assignment(state: GenerationState) -> str:
    return "node_handle_error" if state.get("error") else "node_post_generation"


def build_graph() -> StateGraph:
    g = StateGraph(GenerationState)
    g.add_node("node_topic_discovery", node_topic_discovery)
    g.add_node("node_writer_assignment", node_writer_assignment)
    g.add_node("node_post_generation", node_post_generation)
    g.add_node("node_image_generation", node_image_generation)
    g.add_node("node_handle_error", node_handle_error)
    g.add_node("node_finalize", node_finalize)

    g.set_entry_point("node_topic_discovery")
    g.add_conditional_edges(
        "node_topic_discovery",
        _route_after_discovery,
        {"node_handle_error": "node_handle_error", "node_writer_assignment": "node_writer_assignment"},
    )
    g.add_conditional_edges(
        "node_writer_assignment",
        _route_after_assignment,
        {"node_handle_error": "node_handle_error", "node_post_generation": "node_post_generation"},
    )
    g.add_edge("node_post_generation", "node_image_generation")
    g.add_edge("node_image_generation", "node_finalize")
    g.add_edge("node_finalize", END)
    g.add_edge("node_handle_error", END)
    return g


graph = build_graph().compile()
