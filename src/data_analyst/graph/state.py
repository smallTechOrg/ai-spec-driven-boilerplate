from typing import TypedDict


class AgentState(TypedDict, total=False):
    run_id: str
    session_id: str
    dataset_path: str
    dataframe_key: str
    user_question: str
    action_history: list[dict]
    iteration_count: int
    llm_response: str
    final_answer: str | None
    tokens_input: int
    tokens_output: int
    estimated_cost_usd: float | None
    error: str | None
