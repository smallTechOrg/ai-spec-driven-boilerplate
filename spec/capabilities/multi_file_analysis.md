# Capability: Multi-File Analysis (Phase 2)

## What It Does

Upload multiple CSV or Excel files in one session. Ask questions spanning multiple files — joins, comparisons, independent analysis. All uploaded DataFrames available in exec() sandbox as `dfs` dict.

## Status

**Phase 2 — stub shown in Phase 1 UI with "[Coming in Phase 2]" label**

## Input

- Multiple CSV or Excel (.xlsx) files uploaded to same session
- Questions referencing multiple files by name or implicitly

## Output

Same as single-file Q&A: prose answer + optional Plotly chart.

## Multi-File Context

```python
dfs = {
    "sales": pd.DataFrame(...),
    "customers": pd.DataFrame(...),
}
```

LLM prompt includes schema + stats for ALL files, labelled by filename.

## Excel Support

`.xlsx` files via `pandas.read_excel()` (requires openpyxl). Profile + Q&A identical to CSV. Phase 2 only.

## Phase

Phase 2. Not in Phase 1.

## Phase 1 Stub

Upload dropzone shows "CSV only — Excel support coming in Phase 2". Disabled "Upload another file [Coming in Phase 2]" button below profile card.

## Acceptance Criteria (Phase 2)

- [ ] Upload two CSVs → ask "join these on customer_id" → merged result
- [ ] Upload Excel → profile card correct
- [ ] Upload 3 files → agent answers cross-file question correctly
