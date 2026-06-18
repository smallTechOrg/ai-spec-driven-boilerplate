"""Domain models for datasets and their uploaded files."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ColumnSchema(BaseModel):
    name: str
    type: str


class FileRead(BaseModel):
    id: str
    dataset_id: str
    filename: str
    duckdb_table: str
    schema_columns: list[ColumnSchema]
    row_count: int
    created_at: datetime


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class DatasetRead(BaseModel):
    id: str
    name: str
    created_at: datetime
    files: list[FileRead] = []
