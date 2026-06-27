# Capability: Charts

## What It Does

From query result rows, auto-selects up to 4 chart types based on the data shape, builds a chart specification JSON per chart (axes, series, data points), and returns it for client-side rendering with Recharts in the browser. No server-side image generation occurs.

## Inputs

| Input | Type | Source | Required |
|-------|------|---------|----------|
| `query_rows` | list[dict] | agent state (from execute_sql node) | Yes |
| `question` | string | agent state | Yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `chart_specs` | list[ChartSpec JSON] (up to 4 items) | agent state; persisted to `runs.chart_specs` column; returned in API response |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| None — all logic is deterministic Python | — | — |

## Business Rules

- **Auto-selection logic (priority order, stop at 4 charts):**
  1. **Time-series / line chart:** if any column has a date or datetime dtype and at least one numeric column exists. X-axis = date column; Y-axis = each numeric column as a separate series (max 5 series).
  2. **Bar chart:** if a string/categorical column with 2-30 distinct values exists and at least one numeric column exists. X-axis = categorical column; Y-axis = first numeric column. If more than 30 distinct values exist, take the top 15 by the numeric column value.
  3. **Histogram:** if exactly one numeric column exists and no date column. Bin count = min(20, unique_value_count). If two or more numeric columns exist, generate one histogram for the first numeric column only.
  4. **Scatter / correlation:** if two or more numeric columns exist. X-axis = first numeric column; Y-axis = second numeric column. If a third numeric column exists, encode it as the point size. Maximum 500 data points (sample if larger).
- **Data volume cap:** each chart spec includes at most 500 data points. Rows are sampled uniformly if the result exceeds 500. The `sampled` bool field in ChartSpec records whether sampling occurred.
- **Chart type de-duplication:** if the same chart type would be selected twice (e.g. two bar charts because two categorical columns exist), include only the first.
- **Empty or single-row result:** return `chart_specs = []`. No charts are generated.
- **ChartSpec JSON schema:** `chart_type` (one of `line`, `bar`, `histogram`, `scatter`); `title` (string — human-readable auto-generated title like "Sales by Month"); `x_axis` (`{key, label}`); `y_axes` (list of `{key, label}`); `data` (list of row dicts, max 500); `sampled` (bool).

## Success Criteria

- [ ] A dataset with a date column and two numeric columns produces a line chart spec where `x_axis.key` is the date column name and `y_axes` contains both numeric columns.
- [ ] A dataset with a categorical column (5 distinct values) and one numeric column produces a bar chart spec with 5 data points.
- [ ] A dataset with a single numeric column and no date column produces a histogram spec with `bin_count <= 20`.
- [ ] A dataset with two numeric columns and no date/categorical columns produces a scatter spec.
- [ ] A dataset with 1 000 rows produces a chart spec where `data` has exactly 500 entries and `sampled == true`.
- [ ] An empty `query_rows` returns `chart_specs == []`.
- [ ] All four chart types can be produced independently from fixture data in unit tests (no LLM call needed).
