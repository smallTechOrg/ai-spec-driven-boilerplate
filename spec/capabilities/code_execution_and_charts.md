# Capability: Code Execution and Interactive Charts

## What It Does

Executes LLM-generated Python/pandas code in a sandboxed exec() on the server. Captures result value and optional Plotly figure. Returns Plotly JSON to frontend for interactive rendering.

## Execution Sandbox

exec() restricted namespace:
```python
{
    "dfs": {filename_stem: pd.DataFrame, ...},  # all uploaded DataFrames
    "pd": pandas,
    "np": numpy,
    "go": plotly.graph_objects,
    "px": plotly.express,
}
```

No filesystem access, no network, no imports beyond pre-loaded modules. Timeout: 30 seconds.

## Result Capture

After exec(), inspect namespace for:
- `result`: any value → `str(result)` or `repr(result)`
- `fig`: Plotly Figure → `json.loads(fig.to_json())`

## Chart Rendering

Frontend renders Plotly JSON with react-plotly.js:
- Full-width, 350px height
- Interactive: zoom, pan, hover tooltips
- Never PNG images — always Plotly JSON spec

## Privacy

exec() sandbox has full DataFrame access (needed for pandas ops). `format_response` node receives only `str(result)` — not raw rows.

## Error Handling

- SyntaxError: caught, error message to user
- Runtime exception: caught, traceback summary to user
- Timeout > 30s: killed, timeout message to user
- Phase 3: retry with error-corrected code

## Phase

Phase 1 (real).

## Acceptance Criteria

- [ ] "Show me a bar chart of sales by region" → interactive Plotly bar chart in chat
- [ ] "What is the average revenue?" → text answer with numeric value, no chart
- [ ] Malformed generated code → error message, app does not crash
- [ ] Sandbox cannot import os, sys, subprocess
