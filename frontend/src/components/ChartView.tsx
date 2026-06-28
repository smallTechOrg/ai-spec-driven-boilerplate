'use client'

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ChartSpec } from '../lib/api'

interface ChartViewProps {
  spec: ChartSpec
}

// A small, accessible-leaning categorical palette.
const COLORS = [
  '#4f46e5',
  '#0ea5e9',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#ec4899',
  '#14b8a6',
]

/**
 * Renders the backend-chosen chart from a declarative `chart_spec`.
 * Supports bar / line / pie; the narrate node picks the type from the data
 * shape. Falls back gracefully if the spec has no usable data.
 */
export function ChartView({ spec }: ChartViewProps) {
  const data = Array.isArray(spec.data) ? spec.data : []
  if (data.length === 0) {
    return (
      <p className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
        No chart data was produced for this answer.
      </p>
    )
  }

  return (
    <div className="h-72 w-full" aria-label={`${spec.type} chart of ${spec.y} by ${spec.x}`}>
      <ResponsiveContainer width="100%" height="100%">
        {renderChart(spec, data)}
      </ResponsiveContainer>
    </div>
  )
}

function renderChart(spec: ChartSpec, data: ChartSpec['data']) {
  if (spec.type === 'line') {
    return (
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey={spec.x} tick={{ fontSize: 12, fill: '#475569' }} />
        <YAxis tick={{ fontSize: 12, fill: '#475569' }} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey={spec.y} stroke={COLORS[0]} strokeWidth={2} dot={false} />
      </LineChart>
    )
  }

  if (spec.type === 'pie') {
    return (
      <PieChart>
        <Tooltip />
        <Legend />
        <Pie data={data} dataKey={spec.y} nameKey={spec.x} outerRadius={100} label>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
      </PieChart>
    )
  }

  // Default: bar
  return (
    <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
      <XAxis dataKey={spec.x} tick={{ fontSize: 12, fill: '#475569' }} />
      <YAxis tick={{ fontSize: 12, fill: '#475569' }} />
      <Tooltip />
      <Legend />
      <Bar dataKey={spec.y} radius={[4, 4, 0, 0]}>
        {data.map((_, i) => (
          <Cell key={i} fill={COLORS[i % COLORS.length]} />
        ))}
      </Bar>
    </BarChart>
  )
}
