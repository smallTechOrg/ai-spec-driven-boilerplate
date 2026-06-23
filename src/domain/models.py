"""Pydantic request/response models matching spec/api.md exactly."""
from datetime import datetime

from pydantic import BaseModel


class ColumnSpec(BaseModel):
    name: str
    type: str


class DatasetSummary(BaseModel):
    id: str
    name: str
    table_name: str
    row_count: int
    columns: list[ColumnSpec]
    created_at: datetime


class QueryRequest(BaseModel):
    dataset_id: str
    question: str


class QueryResult(BaseModel):
    id: str
    dataset_id: str
    question: str
    generated_sql: str | None = None
    answer_text: str | None = None
    result_columns: list[str] | None = None
    result_rows: list[list] | None = None
    row_count: int | None = None
    status: str
    error: str | None = None
    created_at: datetime


class AuditEntry(BaseModel):
    id: str
    operation: str
    dataset_id: str | None = None
    query_id: str | None = None
    sql_text: str | None = None
    row_count: int | None = None
    columns: list[str] | None = None
    duration_ms: int
    success: bool
    error_message: str | None = None
    created_at: datetime
