from typing import TypedDict


class AgentState(TypedDict, total=False):
    session_id: str
    action: str               # "profile" | "answer" | "error"
    uploaded_files: list[dict]  # [{file_id, filename, path, profile_json}]
    current_question: str | None
    generated_code: str | None
    execution_result: str | None
    chart_json: dict | None
    answer: str | None
    error: str | None
