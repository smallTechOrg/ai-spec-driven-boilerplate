from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field

SIZE_BANDS: list[str] = ["1-10", "11-50", "51-200", "201-500"]

EU_COUNTRIES: list[str] = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece",
    "Hungary", "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg",
    "Malta", "Netherlands", "Poland", "Portugal", "Romania", "Slovakia",
    "Slovenia", "Spain", "Sweden",
]


class Filters(BaseModel):
    country: str
    industry: str
    size_band: str


class Candidate(BaseModel):
    """A raw discovered SMB before scoring — output of search/extract nodes."""
    name: str
    website: str | None = None
    country: str
    industry: str
    size_band: str
    hq_city: str | None = None
    description: str | None = None


class Lead(BaseModel):
    """A scored lead — final persisted entity."""
    id: str | None = None
    run_id: str | None = None
    name: str
    website: str | None = None
    country: str
    industry: str
    size_band: str
    hq_city: str | None = None
    description: str | None = None
    score: int = Field(ge=0, le=100, default=0)
    rationale: str | None = None
    created_at: datetime | None = None


class Run(BaseModel):
    id: str
    filters: dict
    status: str
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
