from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    non_null: int
    n_unique: int
    min: object | None = None
    max: object | None = None
    sample_values: list = []


class ProfileBody(BaseModel):
    columns: list[ColumnProfile]
    row_count: int
    quality_flags: list | None = None  # P3


class DatasetBody(BaseModel):
    id: str
    name: str
    kind: str
    row_count: int
    column_count: int
    size_bytes: int
    created_at: datetime


class DatasetWithProfile(BaseModel):
    dataset: DatasetBody
    profile: ProfileBody
