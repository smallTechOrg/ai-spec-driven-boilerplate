"""Domain models — pure Pydantic; no SQLAlchemy imports."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RunStatus = Literal["running", "completed", "failed"]
LeadStatus = Literal["new", "contacted", "rejected"]


class SearchCriteria(BaseModel):
    country: str
    industry: str
    size_min: int | None = None
    size_max: int | None = None


class SearchRunCreate(BaseModel):
    country: str
    industry: str
    size_min: int | None = None
    size_max: int | None = None


class SearchRun(BaseModel):
    id: str
    country: str
    industry: str
    size_min: int | None
    size_max: int | None
    status: RunStatus
    error_message: str | None
    lead_count: int | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class Contact(BaseModel):
    """A publicly-discoverable business contact at a company."""
    name: str | None = None
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None


class LeadCreate(BaseModel):
    search_run_id: str
    company_name: str
    domain: str
    website: str | None = None
    country: str
    industry: str | None = None
    headcount_estimate: str | None = None
    why_fit: str | None = None
    contacts: list[Contact] = Field(default_factory=list)
    status: LeadStatus = Field(default="new")


class Lead(BaseModel):
    id: str
    search_run_id: str
    company_name: str
    domain: str
    website: str | None
    country: str
    industry: str | None
    headcount_estimate: str | None
    why_fit: str | None
    contacts: list[Contact] = Field(default_factory=list)
    status: LeadStatus
    created_at: datetime

    model_config = {"from_attributes": True}
