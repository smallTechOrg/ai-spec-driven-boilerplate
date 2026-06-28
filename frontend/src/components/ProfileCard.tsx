import type { Dataset } from '../lib/api'
import { Card } from './ui'

interface ProfileCardProps {
  dataset: Dataset
}

function fmtNum(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—'
  // Compact, readable formatting for stats.
  if (Number.isInteger(n)) return n.toLocaleString()
  return n.toLocaleString(undefined, { maximumFractionDigits: 4 })
}

/**
 * Auto-profile card shown immediately after upload: row count, every column
 * with its type + null count, and basic per-column numeric stats (min/max/mean).
 */
export function ProfileCard({ dataset }: ProfileCardProps) {
  const { profile } = dataset
  return (
    <Card>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-slate-900">{dataset.name}</h2>
          <p className="text-xs text-slate-500">
            {dataset.source_kind.toUpperCase()}
            {dataset.sheet_name ? ` · sheet "${dataset.sheet_name}"` : ''} · auto-profiled
          </p>
        </div>
        <div className="flex gap-4 text-sm">
          <div>
            <span className="font-semibold text-slate-900">{fmtNum(profile.row_count)}</span>{' '}
            <span className="text-slate-500">rows</span>
          </div>
          <div>
            <span className="font-semibold text-slate-900">{profile.columns.length}</span>{' '}
            <span className="text-slate-500">columns</span>
          </div>
        </div>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[34rem] border-collapse text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="py-2 pr-4 font-medium">Column</th>
              <th className="py-2 pr-4 font-medium">Type</th>
              <th className="py-2 pr-4 font-medium">Nulls</th>
              <th className="py-2 pr-4 font-medium">Min</th>
              <th className="py-2 pr-4 font-medium">Max</th>
              <th className="py-2 pr-4 font-medium">Mean</th>
            </tr>
          </thead>
          <tbody>
            {profile.columns.map((col) => (
              <tr key={col.name} className="border-b border-slate-100 last:border-0">
                <td className="py-2 pr-4 font-medium text-slate-800">{col.name}</td>
                <td className="py-2 pr-4">
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                    {col.type}
                  </span>
                </td>
                <td className="py-2 pr-4 text-slate-600">{fmtNum(col.null_count)}</td>
                <td className="py-2 pr-4 text-slate-600">{fmtNum(col.min)}</td>
                <td className="py-2 pr-4 text-slate-600">{fmtNum(col.max)}</td>
                <td className="py-2 pr-4 text-slate-600">{fmtNum(col.mean)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
