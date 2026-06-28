'use client'

import type { DatasetProfile } from '@/lib/api'

function fmtNum(n: number): string {
  return n.toLocaleString()
}

function fmtSample(values: unknown[]): string {
  if (!values || values.length === 0) return '—'
  return values
    .slice(0, 4)
    .map(v => (v === null || v === undefined ? '∅' : String(v)))
    .join(', ')
}

export function ProfilePanel({ dataset }: { dataset: DatasetProfile }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-slate-800">{dataset.name}</h2>
          <p className="text-xs text-slate-500">Profiled locally · raw rows never left this machine</p>
        </div>
        <div className="flex gap-2">
          <Stat label="rows" value={fmtNum(dataset.row_count)} />
          <Stat label="columns" value={fmtNum(dataset.column_count)} />
        </div>
      </header>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-500">
              <th className="px-5 py-2 font-medium">Column</th>
              <th className="px-5 py-2 font-medium">Type</th>
              <th className="px-5 py-2 font-medium text-right">Distinct</th>
              <th className="px-5 py-2 font-medium text-right">Nulls</th>
              <th className="px-5 py-2 font-medium">Sample values</th>
            </tr>
          </thead>
          <tbody>
            {dataset.profile.map(col => (
              <tr key={col.name} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                <td className="px-5 py-2 font-medium text-slate-800">{col.name}</td>
                <td className="px-5 py-2">
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-600">{col.dtype}</span>
                </td>
                <td className="px-5 py-2 text-right tabular-nums text-slate-600">{fmtNum(col.distinct_count)}</td>
                <td className="px-5 py-2 text-right tabular-nums text-slate-600">{fmtNum(col.null_count)}</td>
                <td className="px-5 py-2 text-slate-500">{fmtSample(col.sample_values)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-indigo-50 px-3 py-1.5 text-center">
      <div className="text-lg font-bold leading-none text-indigo-700 tabular-nums">{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-indigo-500">{label}</div>
    </div>
  )
}
