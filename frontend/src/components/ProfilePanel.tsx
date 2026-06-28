'use client'

import type { DatasetBundle, ProfileColumn } from '@/lib/api'

function fmt(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'number') {
    return Number.isInteger(v) ? v.toLocaleString() : v.toLocaleString(undefined, { maximumFractionDigits: 4 })
  }
  return String(v)
}

function rangeLabel(c: ProfileColumn): string {
  const hasMin = c.min !== null && c.min !== undefined && c.min !== ''
  const hasMax = c.max !== null && c.max !== undefined && c.max !== ''
  if (!hasMin && !hasMax) return '—'
  return `${fmt(c.min)} → ${fmt(c.max)}`
}

export default function ProfilePanel({ bundle }: { bundle: DatasetBundle }) {
  const { dataset, profile } = bundle
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-slate-800" title={dataset.name}>
              {dataset.name}
            </h2>
            <p className="text-xs uppercase tracking-wide text-slate-400">{dataset.kind} · active</p>
          </div>
          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-600">
            Ready
          </span>
        </div>
        <dl className="grid grid-cols-2 gap-3">
          <Stat label="Rows" value={dataset.row_count.toLocaleString()} />
          <Stat label="Columns" value={dataset.column_count.toLocaleString()} />
        </dl>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <header className="border-b border-slate-100 px-4 py-2.5">
          <h3 className="text-sm font-semibold text-slate-700">Columns</h3>
          <p className="text-xs text-slate-400">Schema, dtype and value range per column.</p>
        </header>
        <ul className="divide-y divide-slate-100">
          {profile.columns.map(col => (
            <li key={col.name} className="px-4 py-2.5">
              <div className="flex items-baseline justify-between gap-2">
                <span className="truncate font-mono text-xs font-medium text-slate-800" title={col.name}>
                  {col.name}
                </span>
                <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-500">
                  {col.dtype}
                </span>
              </div>
              <dl className="mt-1 grid grid-cols-3 gap-2 text-[11px] text-slate-500">
                <div>
                  <dt className="text-slate-400">range</dt>
                  <dd className="font-mono text-slate-600" title={rangeLabel(col)}>
                    {rangeLabel(col)}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-400">non-null</dt>
                  <dd className="font-mono text-slate-600">{fmt(col.non_null)}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">unique</dt>
                  <dd className="font-mono text-slate-600">{fmt(col.n_unique)}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <dt className="text-[11px] uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className="text-lg font-semibold tabular-nums text-slate-800">{value}</dd>
    </div>
  )
}
