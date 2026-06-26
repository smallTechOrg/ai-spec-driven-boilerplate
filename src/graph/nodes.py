from pathlib import Path
from db.session import create_db_session
from db.models import DatasetRow
from llm.client import LLMClient
from graph.state import AgentState
import pandas as pd
import json
import re
import logging

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "analyst.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8").strip()


def _make_dataframe_context(df: pd.DataFrame, filename: str) -> str:
    """Schema + describe + head(5) as Markdown — no raw rows beyond head(5)."""
    lines = [f"## Dataset: {filename}", ""]
    lines.append("**Schema (column: dtype):**")
    for col, dtype in df.dtypes.items():
        lines.append(f"- {col}: {dtype}")
    lines.append("")
    lines.append("**Summary statistics:**")
    try:
        desc = df.describe(include="all").iloc[:, :50]  # limit to 50 cols
        lines.append(desc.to_markdown())
    except Exception:
        lines.append("(could not compute statistics)")
    lines.append("")
    lines.append("**First 5 rows:**")
    lines.append(df.head(5).to_markdown(index=False))
    return "\n".join(lines)


def load_dataset(state: AgentState) -> AgentState:
    try:
        dataset_id = state.get("dataset_id", "")
        if not dataset_id:
            return {**state, "error": "No dataset_id provided"}
        with create_db_session() as session:
            row = session.get(DatasetRow, dataset_id)
            if row is None:
                return {**state, "error": f"Dataset {dataset_id} not found"}
            file_path = row.file_path
            filename = row.filename
        df = pd.read_csv(file_path)
        ctx = _make_dataframe_context(df, filename)
        return {**state, "dataframe_context": ctx}
    except Exception as exc:
        logger.error("load_dataset failed: %s", exc, exc_info=True)
        return {**state, "error": str(exc)}


def analyze_query(state: AgentState) -> AgentState:
    try:
        system_prompt = _load_prompt()
        ctx = state.get("dataframe_context", "")
        question = state.get("question", "")
        user_turn = f"{ctx}\n\n**Question:** {question}"
        answer = LLMClient().call_model(user_turn, system=system_prompt)
        return {**state, "answer_text": answer, "output_text": answer}
    except Exception as exc:
        logger.error("analyze_query failed: %s", exc, exc_info=True)
        return {**state, "error": str(exc)}


def extract_table(state: AgentState) -> AgentState:
    answer = state.get("answer_text", "")
    # Look for ```table_json ... ``` block
    pattern = r"```table_json\s*([\s\S]*?)```"
    match = re.search(pattern, answer)
    if match:
        try:
            table_data = json.loads(match.group(1).strip())
            if isinstance(table_data, list):
                return {**state, "table_data": table_data}
        except (json.JSONDecodeError, ValueError):
            pass
    return {**state, "table_data": None}


def handle_error(state: AgentState) -> AgentState:
    logger.error("handle_error: run_id=%s error=%s", state.get("run_id"), state.get("error"))
    return {**state, "status": "failed"}


def finalize(state: AgentState) -> AgentState:
    return {**state, "status": "completed"}
