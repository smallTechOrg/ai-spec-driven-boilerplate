"""The privacy gate's summarizer — reduces raw query rows to safe aggregates.

This is the single, STRUCTURAL boundary between the user's raw data and the LLM.
It is a pure function (no LLM, no I/O) so it can be audited and unit-tested in
isolation. Its guarantee:

    No verbatim raw-row cell value can ever appear in its output UNLESS that
    value belongs to a LOW-CARDINALITY categorical column (a grouping key), which
    is a derived/aggregate property of the column — not a row-level secret.

Why cardinality is the structural distinguisher:
    A grouping key (e.g. "gold"/"silver"/"bronze", a region, a product) has a
    small number of distinct values across the WHOLE dataset — it labels groups.
    A row-level secret (a customer name, an order id, a free-text note) is
    high-cardinality: roughly one distinct value per source row. The gate decides
    cardinality against the dataset-wide profile (a set of derived NUMBERS the LLM
    never sees), so a string value crosses only when its column is a genuine
    low-cardinality label — never a per-row secret — regardless of what SELECT the
    planner emitted (including `SELECT *` or a row-level `... LIMIT 20`).

When the dataset profile is unavailable (e.g. a computed/aliased result column
with no source mapping), the gate falls back to a conservative rule that only
treats a column as a label inside a SMALL, genuinely-aggregated result, and never
for a large/raw result. Everything else the LLM sees is a derived NUMBER (counts,
min/max/mean/sum, null counts, distinct counts, value frequencies).
"""
from __future__ import annotations

from numbers import Number
from typing import Any

# Absolute ceiling on distinct values for a column to be treated as a label.
_MAX_LABEL_CARDINALITY = 50
# A column counts as a label only if its distinct count is at most this fraction
# of the dataset row count (so unique-per-row columns never qualify).
_LABEL_CARDINALITY_RATIO = 0.5

# How many derived summary rows the narration table / chart may carry.
_MAX_SUMMARY_ROWS = 50
# Top-N value frequencies emitted per low-cardinality categorical column.
_TOP_N_FREQUENCIES = 25


def _is_number(v: Any) -> bool:
    # bool is a Number subclass but is categorical here, not a measure.
    return isinstance(v, Number) and not isinstance(v, bool)


def _column_kind(values: list[Any]) -> str:
    """Classify a column from its actual values: 'numeric' or 'categorical'."""
    non_null = [v for v in values if v is not None]
    if non_null and all(_is_number(v) for v in non_null):
        return "numeric"
    return "categorical"


def _numeric_summary(values: list[Any]) -> dict[str, Any]:
    nums = [float(v) for v in values if _is_number(v)]
    null_count = sum(1 for v in values if v is None)
    if not nums:
        return {"kind": "numeric", "count": 0, "null_count": null_count}
    total = sum(nums)
    return {
        "kind": "numeric",
        "count": len(nums),
        "null_count": null_count,
        "min": round(min(nums), 6),
        "max": round(max(nums), 6),
        "mean": round(total / len(nums), 6),
        "sum": round(total, 6),
    }


def _profile_cardinality(profile: dict | None, column_name: str) -> tuple[int | None, int | None]:
    """Return (source_distinct_count, dataset_row_count) for a column, if known.

    Looks the result column up by name in the dataset-wide profile. A computed /
    aliased result column (e.g. `total_sales`) has no source mapping → (None, n).
    """
    if not profile:
        return None, None
    dataset_rows = profile.get("row_count")
    for col in profile.get("columns", []):
        if col.get("name") == column_name:
            dc = col.get("distinct_count")
            return (int(dc) if dc is not None else None), dataset_rows
    return None, dataset_rows


def _is_label_column(
    distinct_in_result: int,
    source_distinct: int | None,
    dataset_rows: int | None,
) -> bool:
    """Decide whether a categorical column's values may cross as group labels.

    A column's values may cross ONLY when the dataset-wide profile proves the
    column is low-cardinality: its DATASET-WIDE distinct count is low in absolute
    terms AND a small fraction of the dataset. This is what separates a region
    (4 distinct of 600 rows) from a customer name (600 of 600), even when the
    query slices down to a few rows.

    Conservative-by-default: when no dataset-wide cardinality is known for the
    column (e.g. a computed / aliased result column with no source mapping), the
    values are NEVER emitted. A string value crosses the boundary only on positive
    proof of low cardinality — never by default — so an unmapped column (or a raw
    slice of unique values) can never leak.
    """
    if distinct_in_result == 0:
        return False
    if source_distinct is None:
        return False
    if source_distinct > _MAX_LABEL_CARDINALITY:
        return False
    if dataset_rows and source_distinct >= _LABEL_CARDINALITY_RATIO * dataset_rows:
        return False
    return True


def _distinct_non_null(values: list[Any]) -> list[Any]:
    seen: list[Any] = []
    marker: set[Any] = set()
    for v in values:
        if v is None:
            continue
        if v not in marker:
            marker.add(v)
            seen.append(v)
    return seen


def _categorical_summary(
    values: list[Any],
    profile: dict | None,
    column_name: str,
) -> dict[str, Any]:
    null_count = sum(1 for v in values if v is None)
    distinct = _distinct_non_null(values)
    distinct_count = len(distinct)
    source_distinct, dataset_rows = _profile_cardinality(profile, column_name)

    summary: dict[str, Any] = {
        "kind": "categorical",
        "null_count": null_count,
        "distinct_count": distinct_count,
    }
    is_label = _is_label_column(distinct_count, source_distinct, dataset_rows)
    # Emit actual category labels (+ frequencies) ONLY for genuine low-cardinality
    # grouping keys. High-cardinality columns (PII / free text / ids) get counts
    # only — their values NEVER cross.
    if is_label:
        freq: dict[Any, int] = {}
        for v in values:
            if v is None:
                continue
            freq[v] = freq.get(v, 0) + 1
        top = sorted(freq.items(), key=lambda kv: (-kv[1], str(kv[0])))[:_TOP_N_FREQUENCIES]
        summary["value_counts"] = [{"value": k, "count": c} for k, c in top]
        summary["is_label"] = True
    else:
        summary["is_label"] = False
    return summary


def _looks_aggregated(
    column_kinds: dict[str, str],
    column_summaries: dict[str, dict],
    rows: list[dict],
) -> bool:
    """True when the result already looks like a GROUP BY output.

    Conditions (all required):
    - small row count;
    - at least one categorical LABEL column (a grouping dimension) is present;
    - every categorical column is a low-cardinality label column; and
    - the label columns are collectively UNIQUE per row (one row per group) — the
      hallmark of a GROUP BY. This is what separates a real aggregate from an
      arbitrary small raw slice (e.g. `SELECT region, salary LIMIT 5`, where the
      grouping label repeats), so a small slice's raw numeric cells are NOT passed
      through verbatim — they are summarized instead.

    When true, the result can be passed through row-by-row safely: each cell is
    either an aggregate measure or a low-card group label.
    """
    row_count = len(rows)
    if row_count == 0 or row_count > _MAX_SUMMARY_ROWS:
        return False

    label_cols = [
        name
        for name, kind in column_kinds.items()
        if kind == "categorical" and column_summaries[name].get("is_label")
    ]
    # Every categorical column must be a label column (no high-card cells present).
    for name, kind in column_kinds.items():
        if kind == "categorical" and not column_summaries[name].get("is_label"):
            return False
    if not label_cols:
        return False

    # The grouping labels must be unique per row (one row per group).
    seen: set[tuple] = set()
    for r in rows:
        key = tuple(r.get(c) for c in label_cols)
        if key in seen:
            return False
        seen.add(key)
    return True


def _passthrough_table(
    column_names: list[str], rows: list[dict], limit: int
) -> dict[str, Any]:
    """Build a narration table by passing already-aggregated rows through.

    Only reached when EVERY categorical column is a low-cardinality label column,
    so no high-cardinality raw value can be present.
    """
    out_rows = [[r.get(c) for c in column_names] for r in rows[:limit]]
    return {"columns": list(column_names), "rows": out_rows}


def _derived_table(
    column_kinds: dict[str, str],
    column_summaries: dict[str, dict],
) -> dict[str, Any]:
    """Build a narration table from LOCAL summaries for a raw / row-level result.

    Pick the most useful low-cardinality label column as the grouping dimension
    and report per-group frequencies; otherwise emit numeric column summaries as a
    small stat table. Either way the cells are derived numbers + low-card labels
    only — never raw rows.
    """
    label_cols = [
        name
        for name, kind in column_kinds.items()
        if kind == "categorical" and column_summaries[name].get("is_label")
    ]
    if label_cols:
        dim = max(label_cols, key=lambda n: column_summaries[n]["distinct_count"])
        vc = column_summaries[dim].get("value_counts", [])
        rows = [[item["value"], item["count"]] for item in vc]
        return {"columns": [dim, "count"], "rows": rows}

    numeric_cols = [n for n, k in column_kinds.items() if k == "numeric"]
    rows = []
    for name in numeric_cols:
        s = column_summaries[name]
        rows.append(
            [name, s.get("count", 0), s.get("min"), s.get("max"), s.get("mean"), s.get("sum")]
        )
    return {"columns": ["column", "count", "min", "max", "mean", "sum"], "rows": rows}


def build_aggregates(
    rows: list[dict],
    columns: list[dict] | None,
    profile: dict | None = None,
) -> dict[str, Any]:
    """Reduce raw query rows to a privacy-safe aggregate object for the LLM.

    Returns an `aggregates` dict containing ONLY derived numbers, column metadata,
    and (for low-cardinality grouping columns) category labels + frequencies.
    Raw, high-cardinality cell values (PII, free text, ids) NEVER appear. The
    dataset `profile` (derived numbers only) supplies dataset-wide cardinality so
    a grouping label crossing is judged against the whole dataset, not a slice.
    """
    rows = rows or []
    row_count = len(rows)

    if columns:
        column_names = [c["name"] for c in columns]
    elif rows:
        column_names = list(rows[0].keys())
    else:
        column_names = []

    by_column: dict[str, list[Any]] = {name: [] for name in column_names}
    for r in rows:
        for name in column_names:
            by_column[name].append(r.get(name))

    column_kinds: dict[str, str] = {
        name: _column_kind(by_column[name]) for name in column_names
    }

    column_summaries: dict[str, dict] = {}
    for name in column_names:
        if column_kinds[name] == "numeric":
            column_summaries[name] = _numeric_summary(by_column[name])
        else:
            column_summaries[name] = _categorical_summary(
                by_column[name], profile, name
            )

    if _looks_aggregated(column_kinds, column_summaries, rows):
        table = _passthrough_table(column_names, rows, _MAX_SUMMARY_ROWS)
        result_kind = "pre_aggregated"
    else:
        table = _derived_table(column_kinds, column_summaries)
        result_kind = "row_level_summary"

    return {
        "result_kind": result_kind,   # "pre_aggregated" | "row_level_summary"
        "row_count": row_count,
        "columns": [{"name": n, "type": column_kinds[n]} for n in column_names],
        "column_summaries": column_summaries,
        "table": table,               # narration/chart-ready, derived data only
        "truncated": row_count > _MAX_SUMMARY_ROWS,
    }
