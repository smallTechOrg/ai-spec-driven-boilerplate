import re
import time
from pathlib import Path

import guardrails
import memory
from config.settings import get_settings
from graph.state import AgentState, NodeTrace
from llm.client import LLMClient
from llm.router import get_router
from observability.events import get_logger
from tools import sandbox
from tools.dataset import load_and_describe, load_dataframe
from tools.registry import default_registry

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_log = get_logger("nodes")

# Human-readable error surfaced when an LLM call fails (no stack traces to UI).
_LLM_UNAVAILABLE = "The analysis service is unavailable, please retry."


def _load_prompt(filename: str = "transform.md") -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


def _enter(state: AgentState, node: str) -> float:
    _log.info("node.start", run_id=state.get("run_id"), node=node)
    return time.monotonic()


def _exit(state: AgentState, node: str, t0: float) -> list[NodeTrace]:
    duration_ms = round((time.monotonic() - t0) * 1000, 2)
    _log.info("node.end", run_id=state.get("run_id"), node=node, duration_ms=duration_ms)
    trace = list(state.get("node_trace") or [])
    trace.append(NodeTrace(node=node, duration_ms=duration_ms))
    return trace


def transform_text(state: AgentState) -> AgentState:
    t0 = _enter(state, "transform_text")
    try:
        prompt_template = _load_prompt()
        # Route the capability work through the "tools" task. Blank route →
        # provider default (byte-identical to before); set AGENT_MODEL_TOOLS to
        # route this call to a specific tier. The react node (Phase 2) is where
        # routing earns its keep; here it proves the wiring end to end.
        response = LLMClient().call_model(
            f"{prompt_template}\n\nInput: {state['input_text']}",
            model=get_router().route("tools"),
        )
        _log.info(
            "llm.call",
            run_id=state.get("run_id"),
            model=response.model,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
            cost_usd=response.cost_usd,
        )
        return {
            **state,
            "output_text": response.text,
            "tokens_in": (state.get("tokens_in") or 0) + response.tokens_in,
            "tokens_out": (state.get("tokens_out") or 0) + response.tokens_out,
            "cost_usd": (state.get("cost_usd") or 0.0) + response.cost_usd,
            "model": response.model,
            "node_trace": _exit(state, "transform_text", t0),
        }
    except Exception as exc:
        _log.error("node.error", run_id=state.get("run_id"), node="transform_text", error=str(exc))
        return {**state, "error": str(exc), "node_trace": _exit(state, "transform_text", t0)}


def _accumulate(state: AgentState, response) -> dict:
    """Fold an LLMResponse's usage into the cumulative observability counters."""
    _log.info(
        "llm.call", run_id=state.get("run_id"), model=response.model,
        tokens_in=response.tokens_in, tokens_out=response.tokens_out,
        cost_usd=response.cost_usd,
    )
    return {
        "tokens_in": (state.get("tokens_in") or 0) + response.tokens_in,
        "tokens_out": (state.get("tokens_out") or 0) + response.tokens_out,
        "cost_usd": (state.get("cost_usd") or 0.0) + response.cost_usd,
        "model": response.model,
    }


# --- Guard + memory seam nodes ----------------------------------------------

def guard_input(state: AgentState) -> AgentState:
    t0 = _enter(state, "guard_input")
    # Analysis path validates `question`; the legacy transform path uses
    # `input_text`. Prefer whichever is populated.
    text = state.get("question") or state.get("input_text") or ""
    patch = {"node_trace": _exit(state, "guard_input", t0)}

    if not text.strip():
        _log.warning("guard.input", run_id=state.get("run_id"), guard_code="EMPTY_QUESTION")
        patch.update(error="Please ask a question about the data.", guard_code="EMPTY_QUESTION")
        return {**state, **patch}

    code, msg = guardrails.check_input(text)
    if code:
        _log.warning("guard.input", run_id=state.get("run_id"), guard_code=code)
        patch.update(error=msg, guard_code=code)
    return {**state, **patch}


def load_memory(state: AgentState) -> AgentState:
    t0 = _enter(state, "load_memory")
    ctx = memory.load_session(state.get("conversation_id", ""))
    return {**state, "memory_context": ctx, "node_trace": _exit(state, "load_memory", t0)}


def react(state: AgentState) -> AgentState:
    """The agentic spine: think → act → observe, one model turn per visit.
    Self-loops (via after_react) while the model calls tools and the budget
    holds. transform_text remains the bare 0-tool slot; this is the active node.
    """
    t0 = _enter(state, "react")
    try:
        client = LLMClient()
        registry = default_registry()
        provider = client.provider_name

        # Seed the message history on the first visit.
        messages = list(state.get("messages") or [])
        if not messages:
            user_text = state["input_text"]
            ctx = state.get("memory_context") or ""
            content = f"{ctx}\n\n{user_text}" if ctx else user_text
            messages = [_user_turn(provider, content)]

        system = _load_prompt("react.md")
        response = client.call_model(
            "", system=system, model=get_router().route("tools"),
            tools=registry.schemas_for(provider), messages=messages,
        )
        patch = _accumulate(state, response)
        patch["iterations"] = state.get("iterations", 0) + 1
        patch["output_text"] = response.text
        messages.append(client.assistant_turn(response))

        if response.tool_calls:
            # ACT + OBSERVE: run each tool, append results, loop.
            results = [(tc.id, registry.dispatch(tc.name, tc.args)) for tc in response.tool_calls]
            names = [tc.name for tc in response.tool_calls]
            messages.append(client.tool_results_turn(results, names=names))
            # Budget meter blocks only when we'd otherwise loop again.
            code, msg = guardrails.budget_exceeded({**state, **patch})
            if code:
                _log.warning("guard.budget", run_id=state.get("run_id"), guard_code=code)
                patch.update(error=msg, guard_code=code)
        patch["messages"] = messages
        patch["node_trace"] = _exit(state, "react", t0)
        return {**state, **patch}
    except Exception as exc:
        _log.error("node.error", run_id=state.get("run_id"), node="react", error=str(exc))
        return {**state, "error": str(exc), "node_trace": _exit(state, "react", t0)}


def guard_output(state: AgentState) -> AgentState:
    t0 = _enter(state, "guard_output")
    code, msg = guardrails.check_output(state.get("output_text", "") or "")
    patch = {"node_trace": _exit(state, "guard_output", t0)}
    if code:
        _log.warning("guard.output", run_id=state.get("run_id"), guard_code=code)
        patch.update(error=msg, guard_code=code)
    return {**state, **patch}


def write_memory(state: AgentState) -> AgentState:
    t0 = _enter(state, "write_memory")
    cid = state.get("conversation_id", "")
    if cid:
        memory.append_turn(cid, "user", state.get("input_text", ""))
        memory.append_turn(cid, "assistant", state.get("output_text", "") or "")
    return {**state, "node_trace": _exit(state, "write_memory", t0)}


def _user_turn(provider: str, content: str) -> dict:
    if provider == "gemini":
        return {"role": "user", "parts": [{"text": content}]}
    return {"role": "user", "content": content}


# --- Analysis capability nodes ----------------------------------------------

_FENCE_RE = re.compile(r"```(?:python|py)?\s*\n?(.*?)```", re.DOTALL | re.IGNORECASE)


def _strip_code_fences(text: str) -> str:
    """Defensively unwrap model output to clean pandas the sandbox can exec.

    Handles ```python ... ``` / ``` ... ``` fences (returns the first fenced
    block if present) and strips stray surrounding prose/backticks/whitespace.
    """
    if not text:
        return ""
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    # No fence: drop any stray leading/trailing backticks and whitespace.
    return text.strip().strip("`").strip()


def load_dataset(state: AgentState) -> AgentState:
    """LOCAL — read the uploaded CSV, derive schema + bounded sample. No LLM."""
    t0 = _enter(state, "load_dataset")
    try:
        described = load_and_describe(state["df_path"])
        return {
            **state,
            "schema": described["schema"],
            "sample": described["sample"],
            "row_count": described["row_count"],
            "node_trace": _exit(state, "load_dataset", t0),
        }
    except Exception as exc:
        _log.error("node.error", run_id=state.get("run_id"), node="load_dataset", error=str(exc))
        # dataset.py raises human-readable ValueErrors ("Could not read this file…").
        return {**state, "error": str(exc), "node_trace": _exit(state, "load_dataset", t0)}


def propose_code(state: AgentState) -> AgentState:
    """LLM — schema + bounded sample + question ONLY. Never the full df."""
    t0 = _enter(state, "propose_code")
    try:
        system = _load_prompt("transform.md")
        prompt_parts = [
            f"SCHEMA:\n{state.get('schema')}",
            f"SAMPLE:\n{state.get('sample')}",
            f"QUESTION:\n{state.get('question', '')}",
        ]
        prior_error = state.get("exec_error")
        if prior_error:
            prompt_parts.append(
                "Your previous code FAILED with this error. Fix it and return "
                f"corrected code:\n{prior_error}"
            )
        memory_context = state.get("memory_context")
        if memory_context:
            prompt_parts.append(f"CONVERSATION CONTEXT:\n{memory_context}")

        response = LLMClient().call_model(
            "\n\n".join(prompt_parts),
            system=system,
            model=get_router().route("tools"),
        )
        patch = _accumulate(state, response)
        code = _strip_code_fences(response.text)
        _log.info(
            "code.proposed",
            run_id=state.get("run_id"),
            repair_attempt=state.get("repair_attempts", 0),
            code_len=len(code),
        )
        patch["proposed_code"] = code
        patch["node_trace"] = _exit(state, "propose_code", t0)
        return {**state, **patch}
    except Exception as exc:
        _log.error("node.error", run_id=state.get("run_id"), node="propose_code", error=str(exc))
        return {
            **state,
            "error": _LLM_UNAVAILABLE,
            "node_trace": _exit(state, "propose_code", t0),
        }


def execute_code(state: AgentState) -> AgentState:
    """LOCAL sandbox — exec the proposed code over the FULL df reloaded from disk."""
    t0 = _enter(state, "execute_code")
    try:
        df = load_dataframe(state["df_path"])
        out = sandbox.run(state.get("proposed_code", ""), df)
        if out.get("ok"):
            return {
                **state,
                "code_result": out["result"],
                "exec_error": None,
                "node_trace": _exit(state, "execute_code", t0),
            }
        err = out.get("error") or "Code execution failed."
        return {
            **state,
            "exec_error": err,
            "repair_attempts": state.get("repair_attempts", 0) + 1,
            "node_trace": _exit(state, "execute_code", t0),
        }
    except Exception as exc:
        # Reloading the df should not fail here (load_dataset already validated),
        # but contain anything and route to a graceful failure.
        _log.error("node.error", run_id=state.get("run_id"), node="execute_code", error=str(exc))
        return {
            **state,
            "exec_error": "Could not execute the analysis code.",
            "repair_attempts": state.get("repair_attempts", 0) + 1,
            "node_trace": _exit(state, "execute_code", t0),
        }


def explain_result(state: AgentState) -> AgentState:
    """LLM — the question + the numeric code_result ONLY. Never the full df."""
    t0 = _enter(state, "explain_result")
    try:
        system = _load_prompt("explain.md")
        prompt = (
            f"QUESTION:\n{state.get('question', '')}\n\n"
            f"RESULT:\n{state.get('code_result')}"
        )
        response = LLMClient().call_model(
            prompt, system=system, model=get_router().route("tools")
        )
        patch = _accumulate(state, response)
        patch["explanation"] = response.text.strip()
        _log.info("result.explained", run_id=state.get("run_id"))
        patch["node_trace"] = _exit(state, "explain_result", t0)
        return {**state, **patch}
    except Exception as exc:
        _log.error("node.error", run_id=state.get("run_id"), node="explain_result", error=str(exc))
        return {
            **state,
            "error": _LLM_UNAVAILABLE,
            "node_trace": _exit(state, "explain_result", t0),
        }


def _format_answer(value: object) -> str:
    """Render the captured code_result as a human-readable answer string."""
    if value is None:
        return ""
    if isinstance(value, float):
        # Trim noise without lying about precision.
        return f"{value:.6g}"
    return str(value)


def handle_error(state: AgentState) -> AgentState:
    t0 = _enter(state, "handle_error")
    # Ensure a human-readable error even when only exec_error (repair budget
    # exhausted) is set — never surface a raw sandbox/stack message verbatim.
    error = state.get("error")
    if not error:
        if state.get("exec_error"):
            error = "Could not compute an answer for this question."
        else:
            error = "The analysis failed. Please try again."
    _log.error("run.failed", run_id=state.get("run_id"),
               error=error, guard_code=state.get("guard_code"))
    return {
        **state,
        "error": error,
        "status": "failed",
        "node_trace": _exit(state, "handle_error", t0),
    }


def finalize(state: AgentState) -> AgentState:
    t0 = _enter(state, "finalize")
    # Assemble the analysis output (answer + code). QueryRow persistence is owned
    # by run_query so both the completed and failed terminals persist exactly one
    # row with consistent latency (no double-write).
    answer = _format_answer(state.get("code_result"))
    _log.info(
        "run.complete",
        run_id=state.get("run_id"),
        tokens_in=state.get("tokens_in", 0),
        tokens_out=state.get("tokens_out", 0),
        cost_usd=state.get("cost_usd", 0.0),
        model=state.get("model"),
    )
    return {
        **state,
        "answer": answer,
        "code": state.get("proposed_code", ""),
        "status": "completed",
        "node_trace": _exit(state, "finalize", t0),
    }
