"""Pydantic models for the ask + run-audit contract (spec/api.md).

These field names are binding — the frontend builds to this contract.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---- request ----

class AskRequest(BaseModel):
    dataset_id: str
    question: str


# ---- narration sub-models (also what the narrate LLM node returns) ----

class KeyStat(BaseModel):
    label: str
    value: Any
    unit: str | None = None


class ChartSpec(BaseModel):
    type: str
    x: str | None = None
    y: str | None = None
    series: str | None = None
    data: list[dict[str, Any]] = Field(default_factory=list)


class SummaryTable(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)


class Narration(BaseModel):
    """The structured output the narrate node parses from Gemini."""

    answer: str = ""
    key_stats: list[KeyStat] = Field(default_factory=list)
    chart_spec: ChartSpec | None = None
    summary_table: SummaryTable | None = None
    insight: str = ""


class Plan(BaseModel):
    """The structured output the plan node parses from Gemini."""

    steps: list[str] = Field(default_factory=list)
    sql: str = ""


class Cost(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    est_usd: float = 0.0


# ---- responses ----

class AskResponse(BaseModel):
    run_id: str
    status: str                       # "completed" | "failed"
    answer: str = ""
    key_stats: list[KeyStat] = Field(default_factory=list)
    chart_spec: ChartSpec | None = None
    summary_table: SummaryTable | None = None
    insight: str = ""
    follow_ups: list[str] = Field(default_factory=list)
    plan_steps: list[str] = Field(default_factory=list)
    generated_sql: str = ""
    cost: Cost = Field(default_factory=Cost)
    error: str | None = None          # populated on status="failed"


class RunListItem(BaseModel):
    id: str
    dataset_id: str | None = None
    status: str
    question: str | None = None
    generated_sql: str | None = None
    est_usd: float | None = None
    created_at: str | None = None


class RunListResponse(BaseModel):
    runs: list[RunListItem]


class RunDetail(BaseModel):
    id: str
    dataset_id: str | None = None
    status: str
    question: str | None = None
    plan_steps: list[str] = Field(default_factory=list)
    generated_sql: str | None = None
    result_summary: dict[str, Any] | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    est_usd: float | None = None
    error: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
