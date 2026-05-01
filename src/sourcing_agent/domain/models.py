from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SourcingRequest(BaseModel):
    id: str
    material: str
    quantity: str
    location: str
    budget: str | None = None
    timeline: str | None = None
    criteria: str | None = None
    created_at: datetime


class Run(BaseModel):
    id: str
    request_id: str
    status: str = "pending"
    llm_provider: str
    search_provider: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class Supplier(BaseModel):
    id: str
    run_id: str
    name: str
    location: str | None = None
    price_indication: str | None = None
    lead_time: str | None = None
    source_url: str | None = None
    notes: str | None = None
    google_rating: float | None = None
    google_review_count: int | None = None
    feedback_summary: str | None = None
    delivery_reliability: str | None = None
    years_in_business: int | None = None
    solvency_signal: str | None = None
    gst_registered: bool | None = None


class Recommendation(BaseModel):
    id: str
    run_id: str
    supplier_id: str
    rank: int
    score: int = Field(ge=0, le=100)
    rationale: str
