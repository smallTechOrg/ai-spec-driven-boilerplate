'use client'

import { useState } from 'react'
import type { Query } from '../lib/api'
import { ComingSoonBadge } from './ComingSoon'

function ResultTable({ columns, rows }: { columns: string[]; rows: (string | number | null)[][] }) {
  if (columns.length === 0) {
    return <p className="text-sm text-gray-400">Query returned no columns.</p>
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            {columns.map(col => (
              <th
                key={col}
                className="whitespace-nowrap px-3 py-2 text-left font-semibold text-gray-700"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-3 py-4 text-center text-gray-400">
                No rows matched this query.
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50">
                {row.map((cell, j) => (
                  <td key={j} className="whitespace-nowrap px-3 py-2 text-gray-800">
                    {cell === null ? <span className="text-gray-300">—</span> : String(cell)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}

export function AnswerView({ query }: { query: Query }) {
  const [showSql, setShowSql] = useState(false)
  const failed = query.status === 'failed'

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">Question</p>
          <p className="mt-0.5 text-base font-medium text-gray-900">{query.question}</p>
        </div>
        {/* Chart view — disabled stub for Phase 3 */}
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            disabled
            aria-disabled="true"
            title="Chart view — Coming soon (Phase 3)"
            className="cursor-not-allowed rounded-md border border-gray-200 px-2.5 py-1 text-xs font-medium text-gray-400"
          >
            Chart view
          </button>
          <ComingSoonBadge />
        </div>
      </div>

      {failed ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm font-semibold text-red-700">This query failed</p>
          <p className="mt-1 text-sm text-red-600">
            {query.error ?? 'The query could not be completed.'}
          </p>
        </div>
      ) : (
        <>
          {query.answer_text && (
            <div className="mb-4 whitespace-pre-wrap rounded-lg bg-blue-50/60 p-4 text-sm leading-relaxed text-gray-800">
              {query.answer_text}
            </div>
          )}
          <ResultTable columns={query.result_columns} rows={query.result_rows} />
        </>
      )}

      {query.generated_sql && (
        <div className="mt-4">
          <button
            type="button"
            onClick={() => setShowSql(s => !s)}
            className="text-xs font-medium text-blue-600 hover:text-blue-700"
            aria-expanded={showSql}
          >
            {showSql ? 'Hide SQL' : 'Show SQL'}
          </button>
          {showSql && (
            <pre className="mt-2 overflow-x-auto rounded-lg bg-gray-900 p-3 font-mono text-xs leading-relaxed text-gray-100">
              {query.generated_sql}
            </pre>
          )}
        </div>
      )}
    </section>
  )
}
