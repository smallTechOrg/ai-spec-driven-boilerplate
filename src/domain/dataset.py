from pydantic import BaseModel
from datetime import datetime
from typing import List


class DatasetResponse(BaseModel):
    dataset_id: str
    session_id: str
    filename: str
    row_count: int
    column_names: List[str]
    created_at: datetime


class DatasetListResponse(BaseModel):
    datasets: List[DatasetResponse]
