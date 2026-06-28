'use client'

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ChartSpec } from '@/lib/api'

interface Props {
  spec: ChartSpec
  rows: Record<string, unknown>[]
}

const COLOR = '#6366f1'

function toNumber(v: unknown): number | null {
  if (typeof v === 'number') return v
  if (typeof v === 'string' && v.trim() !== '' && !isNaN(Number(v))) return Number(v)
  return null
}

export function ResultChart({ spec, rows }: Props) {
  if (!rows || rows.length === 0) return null
  const { chart_type, x, y } = spec
  const data = rows
    .map(r => ({ ...r, [y]: toNumber(r[y]) }))
    .filter(r => r[y] !== null)

  if (data.length === 0) return null

  const type = (chart_type || 'bar').toLowerCase()

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      {spec.title && <h4 className="mb-3 text-sm font-semibold text-slate-700">{spec.title}</h4>}
      <ResponsiveContainer width="100%" height={280}>
        {type === 'line' ? (
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
            <XAxis dataKey={x} tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <Tooltip />
            <Line type="monotone" dataKey={y} stroke={COLOR} strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        ) : type === 'scatter' ? (
          <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
            <XAxis dataKey={x} tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <YAxis dataKey={y} tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <Tooltip cursor={{ strokeDasharray: '3 3' }} />
            <Scatter data={data} fill={COLOR} />
          </ScatterChart>
        ) : (
          <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
            <XAxis dataKey={x} tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <Tooltip cursor={{ fill: '#f1f5f9' }} />
            <Bar dataKey={y} fill={COLOR} radius={[4, 4, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
