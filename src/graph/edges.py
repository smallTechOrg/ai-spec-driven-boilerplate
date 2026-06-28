from graph.state import AgentState


def route_on_error(state: AgentState, next_node: str) -> str:
    """Route to `handle_error` if a node set state["error"], else to next_node.

    This is the single conditional used after every fatal node, so the privacy
    boundary and error handling are properties of the graph topology.
    """
    if state.get("error"):
        return "handle_error"
    return next_node
