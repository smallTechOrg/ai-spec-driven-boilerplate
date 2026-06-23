# Capability: Response Formatting

## What It Does

Converts the raw SQL result rows and optional SQL explanation from the graph into a human-readable markdown answer string and a cleaned list-of-dicts table ready for the frontend to render.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `sql_explanation` | string (optional) | `query_planner` node via AnalystState | No |
| `rows` | list of dicts (≤ 1,000) | `sql_executor` node via AnalystState | Yes (may be empty list) |
| `row_count` | int | `sql_executor` node via AnalystState | Yes |
| `sql` | string | `query_planner` node via AnalystState | Yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `answer` | string (markdown) | AnalystState → POST /query response body |
| `table` | list of dicts (cleaned) | AnalystState → POST /query response body |

## External Calls

None. `response_formatter` is a pure in-process transformation node with no external I/O.

## Business Rules

- **Empty results:** If `rows` is an empty list, set `answer = "No results found."` and `table = []`.
- **Normal results:** If `sql_explanation` is set, use it as the opening sentence of `answer`. Append a summary line: `"Returned {row_count} row(s)."`.
- **Null rendering:** Any `None` value in a row dict is rendered as the string `"—"` in both `answer` (if referenced) and `table`.
- **String truncation:** Any string value longer than 50 characters is truncated to 50 characters with `…` appended. Applied to both `answer` table references and `table` dict values.
- **Degraded fallback:** If an unexpected exception occurs inside `response_formatter`, set `answer = "Could not format result."` and `table = []`. Never set `state["error"]` — this node must never cause graph routing to `handle_error`.
- **`table` output:** A copy of `rows` with null and truncation transformations applied. Column keys are preserved exactly as returned by SQLAlchemy.

## Success Criteria

- [ ] When `rows` is non-empty, `answer` contains a non-empty markdown string and `table` matches the row data
- [ ] When `rows` is an empty list, `answer` is exactly `"No results found."` and `table` is `[]`
- [ ] Null values in any row appear as `"—"` in the returned `table`
- [ ] String values longer than 50 characters are truncated to 50 chars + `…` in the returned `table`
- [ ] An unexpected exception inside `response_formatter` results in `answer = "Could not format result."` rather than a graph error
- [ ] `state["error"]` is never set by `response_formatter`
