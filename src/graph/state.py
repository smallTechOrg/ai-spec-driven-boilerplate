from typing import TypedDict


class AgentState(TypedDict, total=False):
    run_id: str
    session_id: str
    dataset_id: str
    dataset_ids: list[str]
    question: str
    dataframe_context: str
    answer_text: str
    table_data: list[dict] | None
    chart_b64: str | None
    error: str | None
    # backward-compat fields (kept so old /runs endpoint still works)
    input_text: str
    output_text: str
