from typing import TypedDict


class AgentState(TypedDict, total=False):
    run_id: str
    query_record_id: str
    dataset_id: str
    question: str
    csv_path: str
    column_names: list[str]
    row_count: int
    data_sample: str
    answer: str
    error: str | None
