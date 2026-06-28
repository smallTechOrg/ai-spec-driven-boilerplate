"""Pydantic models for the dataset upload contract (spec/api.md)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ColumnProfile(BaseModel):
    name: str
    type: str
    null_count: int
    min: float | None = None
    max: float | None = None
    mean: float | None = None


class DatasetProfile(BaseModel):
    row_count: int
    columns: list[ColumnProfile]


class DatasetEntry(BaseModel):
    id: str
    name: str
    source_kind: str          # "csv" | "excel"
    sheet_name: str | None = None
    row_count: int
    profile: DatasetProfile


class UploadResponse(BaseModel):
    datasets: list[DatasetEntry]

    @classmethod
    def from_ingested(cls, ingested: list[Any]) -> "UploadResponse":
        entries = [
            DatasetEntry(
                id=d.id,
                name=d.name,
                source_kind=d.source_kind,
                sheet_name=d.sheet_name,
                row_count=d.row_count,
                profile=DatasetProfile(**d.profile),
            )
            for d in ingested
        ]
        return cls(datasets=entries)
