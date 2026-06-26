from pydantic import BaseModel
from typing import List, Optional, Any


class QueryRequest(BaseModel):
    question: str
    dataset_id: str


class QueryResponse(BaseModel):
    run_id: str
    status: str
    answer_text: Optional[str] = None
    table_data: Optional[List[dict]] = None
    chart_b64: Optional[str] = None
    error: Optional[str] = None
