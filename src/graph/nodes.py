"""
Analyst graph nodes.

Each node takes an AnalystState and returns a (possibly updated) AnalystState dict.
All imports use bare module names (pythonpath = ["src"] in pyproject.toml).
"""
import json
import logging
import time
from pathlib import Path

from graph.state import AnalystState

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "analyst.md"


def _load_analyst_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8").strip()


def _get_provider():
    from llm.providers.gemini import GeminiProvider
    from config.settings import get_settings
    s = get_settings()
    api_key = s.gemini_api_key
    model = s.llm_model or GeminiProvider.DEFAULT_MODEL
    return GeminiProvider(api_key=api_key, model=model)


# ---------------------------------------------------------------------------
# classify_intent
# ---------------------------------------------------------------------------

def classify_intent(state: AnalystState) -> AnalystState:
    """Classify the user's question as data_query | clarification | off_topic."""
    try:
        provider = _get_provider()
        classification_prompt = (
            "Classify this question into exactly one of: data_query, clarification, off_topic.\n"
            "Reply with only the label, no explanation.\n\n"
            f"Question: {state['question']}"
        )
        result = provider.call_model(classification_prompt)
        intent = result.strip().lower()
        if intent not in ("data_query", "clarification", "off_topic"):
            intent = "data_query"  # default to data_query if unclear
        return {**state, "intent": intent}
    except Exception as exc:
        logger.error("classify_intent failed: %s", exc)
        return {**state, "error": str(exc)}


# ---------------------------------------------------------------------------
# build_schema_context
# ---------------------------------------------------------------------------

def build_schema_context(state: AnalystState) -> AnalystState:
    """Load dataset metadata from SQLite and build a compact schema string."""
    try:
        from db.session import create_db_session
        from db.models import DatasetRow
        from db.duckdb_loader import _safe_view_name
        from sqlalchemy import select

        session_id = state["session_id"]

        with create_db_session() as db:
            rows = db.execute(
                select(DatasetRow).where(DatasetRow.session_id == session_id)
            ).scalars().all()

            if not rows:
                return {**state, "error": "No datasets uploaded for this session."}

            datasets = []
            for row in rows:
                try:
                    columns = json.loads(row.columns_json)
                except (json.JSONDecodeError, TypeError):
                    columns = []

                view_name = _safe_view_name(row.name)
                datasets.append({
                    "name": row.name,
                    "file_path": row.file_path,
                    "file_type": row.file_type,
                    "view_name": view_name,
                    "columns": columns,
                    "row_count": row.row_count,
                })

        # Build compact schema string (cap at 4000 chars)
        schema_lines = []
        for ds in datasets:
            schema_lines.append(
                f"Dataset: {ds['name']} ({ds['row_count']} rows) — view: {ds['view_name']}"
            )
            columns = ds["columns"]
            max_cols = 20
            for col in columns[:max_cols]:
                schema_lines.append(f"  - {col['name']}: {col['type']}")
            if len(columns) > max_cols:
                schema_lines.append(
                    f"  [...{len(columns) - max_cols} more columns]"
                )

        schema_context = "\n".join(schema_lines)
        # Truncate the entire string at 4000 chars if still too long
        if len(schema_context) > 4000:
            schema_context = schema_context[:3997] + "..."

        return {**state, "schema_context": schema_context, "datasets": datasets}
    except Exception as exc:
        logger.error("build_schema_context failed: %s", exc)
        return {**state, "error": str(exc)}


# ---------------------------------------------------------------------------
# call_llm_with_tools
# ---------------------------------------------------------------------------

def call_llm_with_tools(state: AnalystState) -> AnalystState:
    """Call Gemini with function calling to produce a SQL query."""
    try:
        from google.genai import types as genai_types

        provider = _get_provider()
        system_prompt = _load_analyst_prompt()

        # Build the execute_sql tool declaration
        execute_sql_tool = genai_types.Tool(
            function_declarations=[
                genai_types.FunctionDeclaration(
                    name="execute_sql",
                    description="Execute a DuckDB SQL query against the session's datasets",
                    parameters=genai_types.Schema(
                        type=genai_types.Type.OBJECT,
                        properties={
                            "sql": genai_types.Schema(
                                type=genai_types.Type.STRING,
                                description="The SQL query to execute",
                            )
                        },
                        required=["sql"],
                    ),
                )
            ]
        )

        # Build conversation history section
        history_lines = []
        for msg in (state.get("conversation_history") or []):
            role = "User" if msg.get("role") == "user" else "Assistant"
            history_lines.append(f"{role}: {msg.get('content', '')}")
        history_text = "\n".join(history_lines) if history_lines else "(no prior conversation)"

        user_message = (
            f"[SCHEMA CONTEXT]\n{state.get('schema_context', '')}\n\n"
            f"[CONVERSATION HISTORY]\n{history_text}\n\n"
            f"[QUESTION]\n{state['question']}"
        )

        result = provider.call_with_tools(
            user_message,
            tools=[execute_sql_tool],
            system=system_prompt,
        )

        if result is not None:
            # Model returned a function call — extract SQL
            sql = result.get("args", {}).get("sql")
            return {**state, "sql": sql}
        else:
            # Model returned plain text (e.g. a direct answer)
            # Try to get text response via call_model for the narrative
            try:
                text_response = provider.call_model(user_message, system=system_prompt)
                return {**state, "sql": None, "narrative": text_response}
            except Exception:
                return {**state, "sql": None}

    except Exception as exc:
        logger.error("call_llm_with_tools failed: %s", exc)
        return {**state, "error": str(exc)}


# ---------------------------------------------------------------------------
# execute_query
# ---------------------------------------------------------------------------

def _write_query_log(
    *,
    session_id: str,
    message_id: str | None,
    dataset_name: str,
    sql: str,
    row_count: int | None,
    latency_ms: int | None,
    error: str | None,
) -> str | None:
    """Write a QueryLogRow to SQLite. Non-fatal — returns log id or None on failure."""
    try:
        from db.session import create_db_session
        from db.models import QueryLogRow

        with create_db_session() as db:
            log_row = QueryLogRow(
                session_id=session_id,
                message_id=message_id or "",
                dataset_name=dataset_name,
                sql=sql,
                row_count=row_count,
                latency_ms=latency_ms,
                error=error,
            )
            db.add(log_row)
            db.flush()
            return log_row.id
    except Exception as exc:
        logger.warning("Failed to write query log: %s", exc)
        return None


def execute_query(state: AnalystState) -> AnalystState:
    """Run the SQL query against registered DuckDB views and log the result."""
    import duckdb
    from db.duckdb_loader import register_datasets_in_duckdb

    start = time.time()
    datasets = state.get("datasets") or []
    primary_dataset_name = datasets[0].get("name", "unknown") if datasets else "unknown"
    sql = state.get("sql", "")

    conn = duckdb.connect(":memory:")
    try:
        register_datasets_in_duckdb(conn, datasets)
        cursor = conn.execute(sql)
        raw_rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [list(r) for r in raw_rows[:500]]
        row_count = len(raw_rows)
        latency_ms = int((time.time() - start) * 1000)

        query_result = {
            "columns": columns,
            "rows": rows,
            "row_count": row_count,
        }

        log_id = _write_query_log(
            session_id=state["session_id"],
            message_id=state.get("message_id"),
            dataset_name=primary_dataset_name,
            sql=sql,
            row_count=row_count,
            latency_ms=latency_ms,
            error=None,
        )
        return {**state, "query_result": query_result, "query_log_id": log_id}

    except duckdb.Error as exc:
        latency_ms = int((time.time() - start) * 1000)
        _write_query_log(
            session_id=state["session_id"],
            message_id=state.get("message_id"),
            dataset_name=primary_dataset_name,
            sql=sql,
            row_count=None,
            latency_ms=latency_ms,
            error=str(exc),
        )
        return {**state, "query_error": str(exc)}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# format_response
# ---------------------------------------------------------------------------

def _auto_select_chart_type(columns: list[str], rows: list[list]) -> str | None:
    """Determine the best chart type for this result, or None."""
    if not columns or not rows:
        return None

    row_count = len(rows)

    # Detect column types from the data
    date_keywords = {"date", "time", "year", "month", "day", "week", "quarter", "period"}
    numeric_col_indices = []
    date_col_indices = []

    for i, col in enumerate(columns):
        col_lower = col.lower()
        # Check if column name suggests date/time
        if any(kw in col_lower for kw in date_keywords):
            date_col_indices.append(i)
            continue
        # Check if values are numeric
        sample_values = [r[i] for r in rows[:10] if r[i] is not None]
        if sample_values and all(isinstance(v, (int, float)) for v in sample_values):
            numeric_col_indices.append(i)

    # date/time column → line chart
    if date_col_indices:
        return "line"

    # exactly 2 columns (label + value) with ≤8 rows → pie
    if len(columns) == 2 and row_count <= 8 and len(numeric_col_indices) >= 1:
        return "pie"

    # 1 numeric column and ≤20 rows → bar
    if len(numeric_col_indices) >= 1 and row_count <= 20:
        return "bar"

    return None


def _build_chart_spec(columns: list[str], rows: list[list], chart_type: str) -> dict | None:
    """Build a Chart.js-compatible ChartSpec dict from query results."""
    if not chart_type or not rows or not columns:
        return None

    numeric_col_indices = []
    label_col_index = 0

    date_keywords = {"date", "time", "year", "month", "day", "week", "quarter", "period"}

    for i, col in enumerate(columns):
        col_lower = col.lower()
        if any(kw in col_lower for kw in date_keywords):
            label_col_index = i
            continue
        sample_values = [r[i] for r in rows[:10] if r[i] is not None]
        if sample_values and all(isinstance(v, (int, float)) for v in sample_values):
            numeric_col_indices.append(i)

    # Default: first non-numeric column is labels
    if not numeric_col_indices:
        return None

    # The label column is the first non-numeric column (or index 0)
    non_numeric_indices = [i for i in range(len(columns)) if i not in numeric_col_indices]
    if non_numeric_indices:
        label_col_index = non_numeric_indices[0]

    labels = [str(row[label_col_index]) for row in rows]

    chart_datasets = []
    for num_idx in numeric_col_indices:
        chart_datasets.append({
            "label": columns[num_idx],
            "data": [row[num_idx] for row in rows],
        })

    return {
        "type": chart_type,
        "labels": labels,
        "datasets": chart_datasets,
    }


def format_response(state: AnalystState) -> AnalystState:
    """Format the query result into a narrative + chart spec."""
    try:
        # Path 1: query execution error
        if state.get("query_error"):
            narrative = (
                f"I encountered an error running your query: {state['query_error']}. "
                "Please rephrase your question or check the dataset."
            )
            rich_response = {
                "narrative": narrative,
                "query_result": None,
                "chart_spec": None,
                "sql": state.get("sql"),
                "query_log_id": state.get("query_log_id"),
            }
            return {**state, "narrative": narrative, "chart_spec": None, "rich_response": rich_response}

        # Path 2: clarification / off_topic or no SQL (model answered directly)
        if state.get("intent") in ("clarification", "off_topic") or state.get("sql") is None:
            narrative = state.get("narrative")
            if not narrative:
                if state.get("intent") == "off_topic":
                    narrative = "I'm a data analyst assistant. Please ask me questions about your uploaded datasets."
                else:
                    narrative = "Could you please clarify your question? I'm here to help you analyze your data."
            rich_response = {
                "narrative": narrative,
                "query_result": None,
                "chart_spec": None,
                "sql": None,
                "query_log_id": None,
            }
            return {**state, "narrative": narrative, "chart_spec": None, "rich_response": rich_response}

        # Path 3: successful query — call Gemini JSON mode for narrative + chart hint
        query_result = state.get("query_result") or {}
        columns = query_result.get("columns", [])
        rows = query_result.get("rows", [])
        row_count = query_result.get("row_count", 0)
        first_10 = rows[:10]

        provider = _get_provider()
        format_prompt = (
            "Given this SQL query result, write a 2-3 sentence markdown summary for a business analyst.\n"
            "Focus on the key insight. Return a JSON object with exactly these keys:\n"
            '- "narrative": a markdown string summarizing the finding\n'
            '- "chart_type": one of "bar", "line", "pie", or null if no chart is useful\n\n'
            f"Result columns: {columns}\n"
            f"First 10 rows: {first_10}\n"
            f"Total rows: {row_count}"
        )

        narrative = None
        llm_chart_type = None
        try:
            json_text = provider.call_json(format_prompt)
            parsed = json.loads(json_text)
            narrative = parsed.get("narrative", "")
            llm_chart_type = parsed.get("chart_type")
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("format_response JSON parse failed: %s", exc)
            # Fall back: use a plain text response
            try:
                narrative = provider.call_model(
                    f"Summarize this query result in 2-3 sentences for a business analyst:\n"
                    f"Columns: {columns}\nFirst 10 rows: {first_10}\nTotal rows: {row_count}"
                )
            except Exception:
                narrative = f"Query returned {row_count} row(s) across {len(columns)} column(s)."

        # Auto-select chart type (our logic wins if LLM returns something invalid)
        valid_chart_types = {"bar", "line", "pie"}
        auto_chart_type = _auto_select_chart_type(columns, rows)

        chart_type = None
        if llm_chart_type in valid_chart_types:
            chart_type = llm_chart_type
        elif auto_chart_type:
            chart_type = auto_chart_type

        chart_spec = _build_chart_spec(columns, rows, chart_type) if chart_type else None

        rich_response = {
            "narrative": narrative or "",
            "query_result": query_result,
            "chart_spec": chart_spec,
            "sql": state.get("sql"),
            "query_log_id": state.get("query_log_id"),
        }

        return {
            **state,
            "narrative": narrative,
            "chart_spec": chart_spec,
            "rich_response": rich_response,
        }

    except Exception as exc:
        logger.error("format_response failed: %s", exc)
        return {**state, "error": str(exc)}


# ---------------------------------------------------------------------------
# handle_error
# ---------------------------------------------------------------------------

def handle_error(state: AnalystState) -> AnalystState:
    """Persist error to the message record and mark status as failed."""
    error_text = state.get("error") or state.get("query_error") or "Unknown error"
    message_id = state.get("message_id")

    if message_id:
        try:
            from db.session import create_db_session
            from db.models import MessageRow

            with create_db_session() as db:
                msg = db.get(MessageRow, message_id)
                if msg is not None:
                    msg.status = "failed"
                    msg.error = error_text
        except Exception as exc:
            logger.warning("handle_error: could not persist error to DB: %s", exc)

    logger.error(
        "handle_error: session=%s message=%s error=%s",
        state.get("session_id"),
        message_id,
        error_text,
    )
    return {**state, "status": "failed"}


# ---------------------------------------------------------------------------
# finalize
# ---------------------------------------------------------------------------

def finalize(state: AnalystState) -> AnalystState:
    """Persist the completed rich response to the message record."""
    message_id = state.get("message_id")
    rich_response = state.get("rich_response")

    if message_id:
        try:
            from db.session import create_db_session
            from db.models import MessageRow

            content = json.dumps(rich_response) if rich_response is not None else ""

            with create_db_session() as db:
                msg = db.get(MessageRow, message_id)
                if msg is not None:
                    msg.status = "completed"
                    msg.content = content
        except Exception as exc:
            logger.warning("finalize: could not persist response to DB: %s", exc)

    return {**state, "status": "completed"}
