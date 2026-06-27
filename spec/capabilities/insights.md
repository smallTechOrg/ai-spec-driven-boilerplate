# Capability: Insights

## What It Does

Takes query result rows from the nl-to-sql step, computes descriptive statistics and anomaly detection in Python, then calls the LLM to write a plain-English prose narrative covering key metrics, trends, and anomalies. This implements the brief's "analysis-report" capability (spec/capabilities/analysis-report).

## Inputs

| Input | Type | Source | Required |
|-------|------|---------|----------|
| `query_rows` | list[dict] | agent state (from execute_sql node) | Yes |
| `question` | string | agent state | Yes |
| `sql_query` | string | agent state | Yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `insight_json` | JSON object — structured statistics | agent state; persisted to `runs.insight_json` column |
| `insight_text` | string — prose narrative | agent state; persisted to `runs.output_text` column |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini LLM | Generate prose narrative from computed statistics | Set `state.error`; route to handle_error node |

## Business Rules

- **Structured statistics (Python, no LLM):** for every numeric column in query_rows, compute min, max, mean, median, count (non-null), null_count; identify top 3 highest values and bottom 3 lowest values.
- **Anomaly detection (Python):** for each numeric column, flag values more than 3 standard deviations from the column mean. Include at most 2 anomaly entries, ordered by largest z-score. If fewer than 10 rows exist, skip anomaly detection and return an empty anomalies list.
- **Trend detection (Python):** if a date/datetime column is present and the result has 5 or more rows, order by that date column, take the first and last value of each numeric column, and classify direction as `increasing`, `decreasing`, or `flat` (flat means less than 5% relative change).
- **LLM prose call:** send the statistics JSON plus the original user question to Gemini and request a 150-300 word narrative covering key metrics, trends, and up to 2 anomalies. The system prompt instructs the model to interpret numbers rather than repeat them verbatim.
- **Token efficiency:** send only the statistics JSON to the LLM — never raw rows. If the JSON exceeds 4 000 tokens, truncate to the top 5 numeric columns by cardinality.
- **Empty result short-circuit:** if `query_rows` is empty, set `insight_json = {"row_count": 0}` and `insight_text = "The query returned no results."` — no LLM call is made.
- **insight_json schema:** `row_count` (int); `numeric_columns` (object: col_name to `{min, max, mean, median, count, null_count}`); `top3` (object: col_name to list of 3 highest values); `bottom3` (object: col_name to list of 3 lowest values); `anomalies` (list of `{column, value, z_score}`); `trends` (list of `{column, direction, from, to}`); `truncated` (bool).

## Success Criteria

- [ ] For a numeric dataset with 10 or more rows, `insight_json.numeric_columns` contains correct `min`, `max`, `mean` for every numeric column, asserted against pandas `describe()` on the same data.
- [ ] A column containing a synthetic outlier 4 std devs from the mean appears in `insight_json.anomalies` with `z_score > 3`.
- [ ] A dataset with fewer than 10 rows produces `insight_json.anomalies == []`.
- [ ] An empty result set produces `insight_text == "The query returned no results."` and no Gemini call is made.
- [ ] `insight_text` is between 50 and 600 characters for a non-empty result.
- [ ] `insight_json` passes validation against a Pydantic model mirroring the schema above.
