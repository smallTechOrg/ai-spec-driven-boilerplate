from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class Tokens(BaseModel):
    prompt: int = 0
    completion: int = 0
    total: int = 0


class RunBody(BaseModel):
    id: str
    dataset_id: str
    question: str
    answer: str | None = None
    code: str | None = None
    result_summary: dict | None = None
    tokens: Tokens
    cost_usd: float = 0.0
    status: str
    error_message: str | None = None
    assumptions: list | None = None  # P3
    followups: list | None = None    # P3
    viz: dict | None = None          # P4
    steps: list | None = None        # P3
    created_at: datetime
    completed_at: datetime | None = None
