# Capability: Chart Rendering

## What It Does
Renders an interactive Recharts chart (bar, line, or scatter) in the browser from the chart_type, labels, and values returned by the analysis endpoint, with a summary card below it.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| chart_type | string ("bar", "line", "scatter") | POST /analyze response | yes |
| labels | array | POST /analyze response | yes |
| values | array | POST /analyze response | yes |
| summary | string | POST /analyze response | yes |
| question | string | User input (echoed as label above chart) | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| Interactive chart | Recharts component in DOM | Browser |
| Summary card | Rendered text block | Browser, below the chart |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| POST /analyze | Fetch chart data + summary | Show error state with red border and message |

## Business Rules
- chart_type "bar" renders a Recharts BarChart
- chart_type "line" renders a Recharts LineChart
- chart_type "scatter" renders a Recharts ScatterChart
- All charts are wrapped in ResponsiveContainer with width="100%" height={350}
- All charts include CartesianGrid, XAxis (labels), YAxis (values), and Tooltip showing exact values
- While the /analyze request is in-flight, show a loading spinner and disable the Analyze button
- If the /analyze request returns an error, show an error state (red border, error message text)
- The question is shown as a label above the chart
- The summary is shown in a white rounded card below the chart
- The most recent result appears at the top of the ResultsArea
- Multiple results can be stacked (newest first)

## Success Criteria
- [ ] A "bar" chart_type renders a BarChart with the correct labels on XAxis and values on YAxis
- [ ] A "line" chart_type renders a LineChart
- [ ] A "scatter" chart_type renders a ScatterChart
- [ ] Tooltip shows the exact value when hovering over a data point
- [ ] Loading spinner appears while /analyze is in-flight
- [ ] Error state appears and chart area is not rendered when /analyze returns 500
- [ ] Summary text appears in a card below the chart after a successful response
