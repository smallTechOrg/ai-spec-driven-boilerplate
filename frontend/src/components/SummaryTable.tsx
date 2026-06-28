import type { SummaryTable as SummaryTableData } from '../lib/api'

interface SummaryTableProps {
  table: SummaryTableData
}

function fmtCell(value: string | number | null): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') return value.toLocaleString(undefined, { maximumFractionDigits: 4 })
  return value
}

/** Renders the aggregate summary table returned with the answer. */
export function SummaryTable({ table }: SummaryTableProps) {
  if (!table || table.columns.length === 0) return null
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            {table.columns.map((col) => (
              <th key={col} className="border-b border-slate-200 px-3 py-2 font-medium">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, ri) => (
            <tr key={ri} className="odd:bg-white even:bg-slate-50/50">
              {row.map((cell, ci) => (
                <td key={ci} className="border-b border-slate-100 px-3 py-2 text-slate-700 last:border-0">
                  {fmtCell(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
