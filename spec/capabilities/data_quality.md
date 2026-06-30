# Capability: Automatic Data Quality Inspection + Auto-Clean

## What It Does

Before answering any analytical question, automatically inspects every uploaded dataset for quality issues (missing values, duplicates, type mismatches, invalid dates, outliers); applies safe, unambiguous fixes automatically; and surfaces a collapsible amber "Data quality notice" to the user listing what was found and what was fixed — so `plan_and_code` always operates on cleaner data.

## Inputs

| Input | Type | Source | Required |
|-------|------|---------|----------|
| uploaded_files | list[dict] — each with `path`, `filename`, `profile_json` | AgentState | Yes |
| current_question | str | AgentState (set by prior node) | Yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| quality_report | dict \| None | AgentState `quality_report` field; included in API message response |
| clean_actions | list[str] | AgentState `clean_actions` field; human-readable log of auto-fixes applied |
| uploaded_files (mutated) | list[dict] — DataFrames in memory replaced with cleaned copies | AgentState (passed to `plan_and_code` and `execute_code`) |

### `quality_report` shape

```json
{
  "has_issues": true,
  "issues": [
    {"type": "duplicates",    "message": "2 exact duplicate rows detected — removed automatically"},
    {"type": "numeric_coercion", "column": "price",   "message": "Column 'price' appears numeric but is stored as text — coerced to float automatically"},
    {"type": "missing_values",   "column": "revenue", "message": "Column 'revenue': 47 missing values (23.5%)"},
    {"type": "invalid_dates",    "column": "order_date", "message": "Column 'order_date': 5 values could not be parsed as dates"},
    {"type": "outliers",         "column": "revenue", "message": "Column 'revenue': 3 values beyond 3 standard deviations (review recommended)"}
  ],
  "auto_fixed": [
    "Removed 2 duplicate rows",
    "Coerced column 'price' from object to float64"
  ]
}
```

`quality_report` is `null` when no issues are found — in that case the UI shows no notice panel.

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| pandas (local) | DataFrame inspection and in-place mutation | Catch exception, log, set `quality_report = null`, continue to `plan_and_code` unmodified |

**No LLM call.** The entire inspection and auto-clean is deterministic pandas logic.

## Business Rules

- **Inspection runs on every Q&A**, regardless of whether the file was just uploaded or was already in the session.
- **Auto-fix — exact duplicates:** Drop rows where all column values are identical (`df.drop_duplicates()`). Always applied when ≥1 duplicate exists.
- **Auto-fix — numeric string columns:** If dtype is `object` AND 100% of non-null values are parseable as `float` (via `pd.to_numeric(errors='coerce').notna().all()`), coerce the column to float64. Always applied when the condition holds.
- **Report only — missing values:** Columns where null_pct > 0 are flagged with count and percentage. No auto-fill; user decides.
- **Report only — invalid dates:** Columns whose name contains `"date"`, `"time"`, `"dt"`, or `"at"` (case-insensitive) and whose dtype is `object` are checked with `pd.to_datetime(errors='coerce')`; if any values fail to parse, the count is reported. No auto-conversion; user decides.
- **Report only — outliers:** For each numeric column, values beyond ±3 standard deviations from the mean are counted and reported. No auto-removal; user decides.
- **Privacy:** `quality_report` contains ONLY column names, counts, percentages, and statistical thresholds — never raw cell values. The LLM never receives the quality report (it is returned directly from the node without being added to the LLM prompt).
- **Cleaned DataFrames** are stored back into `uploaded_files` in AgentState (as in-memory objects) so `execute_code` picks them up without re-reading from disk.
- **Missing values and outlier detection** use the cleaned DataFrame (post-dedup, post-coercion) to avoid double-counting artifacts.
- **Single inspection pass per Q&A turn** — the node is not re-entered on retry.

## Success Criteria

- [ ] Upload a CSV with 3 exact duplicate rows → `quality_report.auto_fixed` contains "Removed 3 duplicate rows"; `plan_and_code` receives a DataFrame with those rows absent.
- [ ] Upload a CSV where column `"price"` dtype is `object` and all non-null values parse as float → `quality_report.auto_fixed` contains coercion notice; `execute_code` operates on a `float64` `"price"` column.
- [ ] Upload a CSV with a column `"revenue"` having 25% nulls → `quality_report.issues` includes a `missing_values` entry for `"revenue"` with correct count and percentage; no auto-fill applied.
- [ ] Upload a CSV with column `"order_date"` (dtype `object`) containing 2 unparseable date strings → `quality_report.issues` includes an `invalid_dates` entry for `"order_date"` with count 2; no auto-conversion applied.
- [ ] Upload a CSV with a numeric column containing an extreme outlier (> 3 std dev) → `quality_report.issues` includes an `outliers` entry; no auto-removal applied.
- [ ] Upload a perfectly clean CSV → `quality_report` is `null`; no "Data quality notice" panel rendered in the UI.
- [ ] `quality_report` dict never contains raw row values — verified by automated test that asserts no cell content from the input DataFrame appears in the serialised `quality_report` JSON.
- [ ] Collapsible amber "Data quality notice" panel appears above the answer when `quality_report` is non-null; click collapses/expands it.
- [ ] Playwright E2E test: upload dirty CSV → ask question → assert quality notice panel visible → upload clean CSV → ask question → assert no panel.
- [ ] Integration test: `inspect_quality` node processes a 50 000-row CSV with intentional duplicates, numeric strings, null columns, date column with bad values, and outlier column — all six issue types detected correctly (data large enough that a sampled vs full-data difference would be observable).
