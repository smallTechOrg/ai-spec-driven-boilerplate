from graph.agent import profile_graph, qa_graph
from graph.state import AgentState


def run_profile(session_id: str, file_id: str, filename: str, file_path: str) -> dict:
    """Profile a freshly uploaded file. Returns profile dict."""
    initial: AgentState = {
        "session_id": session_id,
        "action": "profile",
        "uploaded_files": [{"file_id": file_id, "filename": filename, "path": file_path}],
    }
    final = profile_graph.invoke(initial)
    return final["uploaded_files"][0]["profile_json"]


def run_question(session_id: str, question: str, uploaded_files: list[dict]) -> dict:
    """Answer a natural-language question. Returns {answer, chart_json}."""
    initial: AgentState = {
        "session_id": session_id,
        "action": "answer",
        "current_question": question,
        "uploaded_files": uploaded_files,
    }
    final = qa_graph.invoke(initial)
    return {
        "answer": final.get("answer"),
        "chart_json": final.get("chart_json"),
        "action": final.get("action", "answer"),
    }
