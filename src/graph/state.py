from typing import TypedDict


class AgentState(TypedDict, total=False):
    # Identity
    run_id: str                     # analysis_run.id
    dataset_id: str                 # which dataset to analyse
    conversation_id: str | None     # P2: thread this run belongs to

    # Input
    question: str                   # the user's natural-language question
    profile: dict                   # schema/profile (cols, dtypes, ranges, row count)
    history: list                   # P2: prior-turn summaries — NEVER raw rows

    # Pipeline data (populated progressively by nodes)
    plan: str                       # plan node output
    code: str                       # generate_code output (pandas snippet)
    result_summary: dict            # execute_local output (bounded; NEVER raw rows)
    exec_error: str | None          # captured code-execution error, if any
    step: int                       # current loop step (0-based)
    max_steps: int                  # hard cap (default 4) — bounds the iterate loop
    attempts: list                  # [{code, result_summary|error}] per step

    # Output
    answer: str                     # finalize: prose answer
    assumptions: list               # P3: flagged assumptions / uncertainty
    followups: list                 # P3: 2-3 suggested follow-up questions
    viz: dict | None                # P4: chart/table spec
    tokens: dict                    # {prompt, completion, total} accumulated
    cost_usd: float                 # accumulated estimated cost
    status: str                     # "completed" | "failed"

    # Control
    error: str | None               # fatal (non-code) error → routes to handle_error
