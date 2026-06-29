"""Pydantic request/response models for the analysis API contract."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SchemaColumn(BaseModel):
    name: str
    type: str


class DatasetSummary(BaseModel):
    """POST /datasets response payload."""

    id: str
    name: str
    row_count: int
    schema_: list[SchemaColumn] = Field(serialization_alias="schema", alias="schema")
    profile: Any | None = None

    model_config = {"populate_by_name": True}


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    """POST /datasets/{id}/ask response payload (the core contract)."""

    run_id: str
    dataset_id: str
    status: str
    question: str
    answer: str | None = None
    sql: str | None = None
    result: list[dict] | None = None
    flagged: bool = False
    error: str | None = None

    # Null placeholders populated in Phases 2-3 (frontend wires stub panels now).
    chart: Any | None = None
    summary_table: Any | None = None
    followups: Any | None = None
    tokens: Any | None = None
