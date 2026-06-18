"""Context assembly (layers 2-3): build the message list for each plan_action call.

Highest-value first, in one place so ordering/budget are consistent
(patterns/memory-and-context.md). Working memory = action_history (graph state);
short-term memory = recent conversation turns. The full dataset is never included —
only the schema summary + a small sample.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from datachat.prompts import load


def _schema_block(schema_summary: str, sample_rows: str) -> str:
    return (
        "## Dataset schema\n"
        f"{schema_summary}\n\n"
        "## Sample rows (small sample for grounding only — query for real numbers)\n"
        f"{sample_rows}"
    )


def _history_block(action_history: list[dict[str, Any]]) -> str:
    if not action_history:
        return ""
    lines = []
    for i, step in enumerate(action_history, 1):
        status = "ERROR" if step.get("is_error") else "ok"
        lines.append(
            f"Step {i} [{status}]: {step.get('description', '')}\n"
            f"  action: {step.get('action', '')}\n"
            f"  result: {step.get('result', '')}"
        )
    return "## What you have done so far\n" + "\n".join(lines)


def build(
    *,
    schema_summary: str,
    sample_rows: str,
    recent_turns: list[dict[str, Any]],
    question: str,
    action_history: list[dict[str, Any]],
) -> list:
    messages: list = [SystemMessage(content=load("system"))]
    messages.append(SystemMessage(content=_schema_block(schema_summary, sample_rows)))

    for turn in recent_turns:
        role = turn.get("role")
        content = turn.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    hist = _history_block(action_history)
    if hist:
        messages.append(SystemMessage(content=hist))

    messages.append(HumanMessage(content=f"Question: {question}"))
    return messages


def summarize_schema(files: list[dict[str, Any]]) -> tuple[str, str]:
    """Turn stored file rows into a compact schema_summary + sample_rows string."""
    schema_parts: list[str] = []
    sample_parts: list[str] = []
    for f in files:
        cols = ", ".join(f"{c['name']} ({c['type']})" for c in f["schema_json"])
        schema_parts.append(f'Table "{f["duckdb_table"]}" ({f["filename"]}): {cols}')
        sample = json.dumps(f["sample_rows_json"][:5], default=str)
        sample_parts.append(f'"{f["duckdb_table"]}" sample: {sample}')
    return "\n".join(schema_parts), "\n".join(sample_parts)
