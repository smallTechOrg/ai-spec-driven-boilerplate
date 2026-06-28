'use client'

export function ResultTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows || rows.length === 0) return null
  const columns = Object.keys(rows[0])
  const shown = rows.slice(0, 100)

  function render(v: unknown): string {
    if (v === null || v === undefined) return '—'
    if (typeof v === 'number') return v.toLocaleString()
    return String(v)
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50">
          <tr className="text-xs uppercase tracking-wide text-slate-500">
            {columns.map(c => (
              <th key={c} className="px-3 py-2 font-medium">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shown.map((row, i) => (
            <tr key={i} className="border-t border-slate-100 hover:bg-slate-50">
              {columns.map(c => (
                <td key={c} className="px-3 py-1.5 tabular-nums text-slate-700">{render(row[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > shown.length && (
        <p className="bg-slate-50 px-3 py-1.5 text-xs text-slate-400">
          Showing first {shown.length} of {rows.length.toLocaleString()} rows.
        </p>
      )}
    </div>
  )
}
