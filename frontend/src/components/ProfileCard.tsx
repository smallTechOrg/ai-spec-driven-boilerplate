import { Dataset } from '@/lib/api'

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`
  const units = ['KB', 'MB', 'GB']
  let v = n / 1024
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v.toFixed(1)} ${units[i]}`
}

function fmtNum(n: number): string {
  if (typeof n !== 'number' || Number.isNaN(n)) return '—'
  return Number.isInteger(n) ? n.toLocaleString() : n.toLocaleString(undefined, { maximumFractionDigits: 3 })
}

// Renders the dataset profile: header stats + a per-column table with dtype, missing,
// distinct, and (for numeric columns) min/max/mean.
export function ProfileCard({ dataset }: { dataset: Dataset }) {
  const { profile } = dataset
  const numeric = profile.numeric_stats ?? {}
  return (
    <section
      aria-label="Dataset profile"
      className="rounded-xl border border-slate-200 bg-white shadow-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-slate-800" title={dataset.name}>
            {dataset.name}
          </h2>
          <p className="mt-0.5 text-xs text-slate-400">
            Active dataset · {dataset.file_type.toUpperCase()}
          </p>
        </div>
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs">
          <div>
            <dt className="text-slate-400">Rows</dt>
            <dd className="font-semibold text-slate-700">{dataset.row_count.toLocaleString()}</dd>
          </div>
          <div>
            <dt className="text-slate-400">Columns</dt>
            <dd className="font-semibold text-slate-700">{profile.columns.length}</dd>
          </div>
          <div>
            <dt className="text-slate-400">Size</dt>
            <dd className="font-semibold text-slate-700">{fmtBytes(dataset.size_bytes)}</dd>
          </div>
        </dl>
      </div>

      <div className="max-h-72 overflow-auto">
        <table className="w-full border-collapse text-left text-xs">
          <thead className="sticky top-0 bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Column</th>
              <th className="px-4 py-2 font-medium">Type</th>
              <th className="px-4 py-2 font-medium text-right">Missing</th>
              <th className="px-4 py-2 font-medium text-right">Distinct</th>
              <th className="px-4 py-2 font-medium text-right">Min</th>
              <th className="px-4 py-2 font-medium text-right">Max</th>
              <th className="px-4 py-2 font-medium text-right">Mean</th>
            </tr>
          </thead>
          <tbody>
            {profile.columns.map(col => {
              const stat = numeric[col.name]
              return (
                <tr key={col.name} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium text-slate-700">{col.name}</td>
                  <td className="px-4 py-2">
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-600">
                      {col.dtype}
                    </span>
                  </td>
                  <td
                    className={`px-4 py-2 text-right tabular-nums ${
                      col.missing > 0 ? 'font-medium text-amber-600' : 'text-slate-500'
                    }`}
                  >
                    {col.missing.toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-slate-500">
                    {col.distinct.toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-slate-500">
                    {stat ? fmtNum(stat.min) : '—'}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-slate-500">
                    {stat ? fmtNum(stat.max) : '—'}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-slate-500">
                    {stat ? fmtNum(stat.mean) : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
