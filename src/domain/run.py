from typing import Any

from pydantic import BaseModel


class AskRequest(BaseModel):
    dataset_id: str
    question: str
    conversation_id: str | None = None


class AskResponse(BaseModel):
    run_id: str
    conversation_id: str
    status: str
    answer: str | None = None
    plan: str | None = None
    code: str | None = None
    result_preview: str | None = None
    iterations: int = 0
    suggestions: list[str] = []
    chart_spec: dict | None = None
    clarifying_question: str | None = None
    tokens: dict[str, int] = {"prompt": 0, "completion": 0}
    cost_usd: float = 0.0
    error_message: str | None = None


class DatasetResponse(BaseModel):
    id: str
    name: str
    file_type: str
    row_count: int
    size_bytes: int
    profile: dict[str, Any]
    created_at: str
