"""Pydantic domain models for the analysis API."""

from __future__ import annotations

from pydantic import BaseModel


class AnalysisRunRequest(BaseModel):
    file_id: str
    question: str
    session_id: str | None = None


class AnalysisRunResponse(BaseModel):
    run_id: str
    answer: str | None = None
    chart_spec: dict | None = None
    status: str
    error: str | None = None
