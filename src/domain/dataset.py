"""Request/response models for the dataset endpoints (Phase 1).

These mirror the contract in ``spec/api.md`` exactly — the frontend
(``frontend/src/lib/api.ts``) consumes these shapes verbatim.
"""

from __future__ import annotations

from pydantic import BaseModel


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    distinct_count: int
    null_count: int
    sample_values: list = []


class DatasetResponse(BaseModel):
    dataset_id: str
    name: str
    row_count: int
    column_count: int
    profile: list[dict]
    sample_rows: list[dict]


class AskRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class TokenUsage(BaseModel):
    prompt: int
    completion: int
    total: int


class AnswerData(BaseModel):
    turn_id: str
    conversation_id: str
    answer: str
    plan: list
    code: str
    # Bare array of row dicts — matches spec/api.md and the frontend
    # (ResultTable takes rows: Record<string, unknown>[]).
    result_table: list
    chart_spec: dict | None
    follow_ups: list
    token_usage: TokenUsage
    estimated_cost_usd: float
    assumptions: list = []
