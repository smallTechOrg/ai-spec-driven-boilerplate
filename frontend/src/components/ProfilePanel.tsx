'use client'

import { Dataset, ProfileColumn, formatBytes } from '@/lib/api'

function range(col: ProfileColumn): string {
  if (col.min !== undefined || col.max !== undefined || col.mean !== undefined) {
    const parts: string[] = []
    if (col.min !== undefined) parts.push(`min ${col.min}`)
    if (col.max !== undefined) parts.push(`max ${col.max}`)
    if (col.mean !== undefined) parts.push(`mean ${Number(col.mean).toFixed(2)}`)
    return parts.join(' · ')
  }
  if (col.top_values?.length) return col.top_values.slice(0, 3).join(', ')
  return '—'
}

export default function ProfilePanel({ dataset }: { dataset: Dataset }) {
  const { profile } = dataset
  return (
    <section
      data-testid="profile-panel"
      className="rounded-xl border border-slate-200 bg-white shadow-sm"
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-100 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-800">
          Profile — <span className="font-mono text-slate-600">{dataset.filename}</span>
        </h2>
        <p className="text-xs text-slate-500">
          {dataset.row_count.toLocaleString()} rows · {dataset.column_count} columns ·{' '}
          {formatBytes(dataset.size_bytes)}
        </p>
      </header>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-xs">
          <thead>
            <tr className="text-slate-500">
              <th className="px-4 py-2 font-medium">Column</th>
              <th className="px-4 py-2 font-medium">Type</th>
              <th className="px-4 py-2 font-medium">Range / top values</th>
              <th className="px-4 py-2 font-medium text-right">Missing</th>
              <th className="px-4 py-2 font-medium text-right">Distinct</th>
            </tr>
          </thead>
          <tbody>
            {profile.columns.map(col => (
              <tr key={col.name} className="border-t border-slate-100">
                <td className="px-4 py-2 font-mono text-slate-800">{col.name}</td>
                <td className="px-4 py-2">
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-600">
                    {col.dtype}
                  </span>
                </td>
                <td className="px-4 py-2 text-slate-600">{range(col)}</td>
                <td className="px-4 py-2 text-right text-slate-600">{col.missing_count}</td>
                <td className="px-4 py-2 text-right text-slate-600">
                  {col.distinct_count ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {profile.sample?.length > 0 && (
        <details className="border-t border-slate-100 px-4 py-3">
          <summary className="cursor-pointer text-xs font-medium text-slate-600">
            Sample rows ({profile.sample.length})
          </summary>
          <pre className="mt-2 max-h-48 overflow-auto rounded bg-slate-50 p-2 text-[11px] text-slate-700">
            {JSON.stringify(profile.sample, null, 2)}
          </pre>
        </details>
      )}
    </section>
  )
}
