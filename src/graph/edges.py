from graph.state import AnalystState


def after_classify(state: AnalystState) -> str:
    if state.get("error"):
        return "handle_error"
    if state.get("intent") in ("clarification", "off_topic"):
        return "format_response"
    return "build_schema_context"


def after_schema(state: AnalystState) -> str:
    if state.get("error"):
        return "handle_error"
    return "call_llm_with_tools"


def after_llm(state: AnalystState) -> str:
    if state.get("error"):
        return "handle_error"
    if state.get("sql") is None:
        return "format_response"
    return "execute_query"


def after_execute(state: AnalystState) -> str:
    if state.get("query_error"):
        return "handle_error"
    return "format_response"


def after_format(state: AnalystState) -> str:
    if state.get("error"):
        return "handle_error"
    return "finalize"
