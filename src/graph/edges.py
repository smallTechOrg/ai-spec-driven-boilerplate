from graph.state import AgentState

# Caps the refine loop — Goal-Setting/Monitoring stop condition (#11).
MAX_ITERATIONS = 3


def route_after_inspect(state: AgentState) -> str:
    """Route out of inspect_result.

    - verdict == "done"                      -> answer
    - verdict == "refine" & iter <  MAX      -> generate_code (refine loop)
    - verdict == "refine" & iter >= MAX      -> answer (best-effort, flagged)
    - (P4) verdict == "clarify"              -> clarify
    """
    verdict = state.get("verdict", "done")
    iteration = state.get("iteration", 0)

    if verdict == "refine" and iteration < MAX_ITERATIONS:
        return "generate_code"
    # "done", clarify-not-wired-in-P1, or refine past the cap -> answer.
    return "answer"
