from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ColumnSchema(BaseModel):
    name: str
    type: str  # DuckDB type string, e.g. "VARCHAR", "DOUBLE", "DATE"


class QueryResultModel(BaseModel):
    columns: list[str]
    rows: list[list[Any]]  # up to 500 rows
    row_count: int          # total rows from DuckDB (may exceed 500)


class ChartSpec(BaseModel):
    type: str           # "bar" | "line" | "pie"
    labels: list[str]   # X-axis labels or pie slice labels
    datasets: list[dict]  # Chart.js dataset objects: {"label": str, "data": list[float]}


class RichResponseModel(BaseModel):
    narrative: str               # markdown text
    query_result: QueryResultModel | None = None
    chart_spec: ChartSpec | None = None
    sql: str | None = None       # the SQL that was executed (shown in UI on hover)
    query_log_id: str | None = None


class DatasetModel(BaseModel):
    dataset_id: str
    session_id: str
    name: str
    file_path: str
    file_type: str
    row_count: int
    columns: list[ColumnSchema]
    uploaded_at: datetime


class MessageModel(BaseModel):
    message_id: str
    session_id: str
    role: str  # "user" | "assistant"
    content: str
    status: str  # "pending" | "completed" | "failed"
    error: str | None = None
    created_at: datetime


class SessionModel(BaseModel):
    session_id: str
    name: str
    created_at: datetime
    dataset_count: int = 0
    message_count: int = 0
