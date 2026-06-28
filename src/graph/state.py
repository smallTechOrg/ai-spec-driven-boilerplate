from typing import Callable, TypedDict


class AgentState(TypedDict, total=False):
    # --- Identity ---
    run_id: str               # turn id; set at initialisation
    dataset_id: str           # input
    conversation_id: str      # input

    # --- Input ---
    question: str             # input (user)
    profile: list             # [{name,dtype,distinct_count,null_count,...}] from Dataset
    sample_rows: list         # capped N-row sample from Dataset
    file_path: str            # path to the real file on disk (executor reads this)
    row_count: int            # true full row count from the dataset profile
    history: list             # prior turns [{question, answer}, ...]

    # --- Pipeline data (populated progressively) ---
    plan: list                # by plan node
    code: str                 # by generate_code
    result_table: dict        # by execute_local  {columns, rows, row_count}
    traceback: str | None     # by execute_local on failure
    retry_count: int          # self-correction guard (max 1)
    answer: str               # by visualize
    chart_spec: dict          # by visualize
    follow_ups: list          # by visualize
    assumptions: list         # set when best-guessing

    # --- Output / accounting ---
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    status: str               # "completed" | "failed"

    # --- Control ---
    error: str | None
    on_step: Callable         # optional SSE hook: on_step(step:str, status:str)

    # --- Back-compat (skeleton transform slot; unused on the analysis path) ---
    input_text: str
    output_text: str
    messages: list
