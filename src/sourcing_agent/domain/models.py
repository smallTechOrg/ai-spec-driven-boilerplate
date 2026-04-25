"""Domain models — typed data contracts between modules."""

from pydantic import BaseModel, Field, field_validator


class SourcingRunStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MaterialRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=50)

    @field_validator("name", "unit")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class SourcingRequest(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=200)
    materials: list[MaterialRequest] = Field(..., min_length=1)

    @field_validator("project_name")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class SupplierCandidateData(BaseModel):
    """A single supplier candidate returned by the research node."""

    supplier_name: str
    supplier_location: str | None = None
    price_per_unit: float
    currency: str = "USD"
    lead_time_days: int
    certifications: list[str] = Field(default_factory=list)
    notes: str | None = None
    # Score is set by the rank node
    score: float = 0.0
