'use client'

import { useState } from 'react'
import type { QueryResult } from '../lib/api'

interface Props {
  result: QueryResult
}

function isNumeric(value: unknown): boolean {
  return typeof value === 'number' || (typeof value === 'string' && !isNaN(Number(value)) && value.trim() !== '')
}

function detectNumericColumns(result: QueryResult): boolean[] {
  return result.columns.map((_, colIdx) => {
    const sample = result.rows.slice(0, 20).map((row) => row[colIdx]).filter((v) => v != null)
    return sample.length > 0 && sample.every(isNumeric)
  })
}

export default function DataTable({ result }: Props) {
  const [sortCol, setSortCol] = useState<number | null>(null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc' | 'none'>('none')

  const numericCols = detectNumericColumns(result)

  const sortedRows =
    sortCol !== null && sortDir !== 'none'
      ? [...result.rows].sort((a, b) => {
          const av = a[sortCol]
          const bv = b[sortCol]
          if (av == null) return 1
          if (bv == null) return -1
          const cmp = av < bv ? -1 : av > bv ? 1 : 0
          return sortDir === 'asc' ? cmp : -cmp
        })
      : result.rows

  function toggleSort(idx: number) {
    if (sortCol !== idx) {
      setSortCol(idx)
      setSortDir('asc')
    } else if (sortDir === 'asc') {
      setSortDir('desc')
    } else if (sortDir === 'desc') {
      setSortDir('none')
      setSortCol(null)
    } else {
      setSortDir('asc')
    }
  }

  function copyCsv() {
    const header = result.columns.join(',')
    const rowsCsv = sortedRows
      .map((row) =>
        row
          .map((cell) => {
            const s = cell == null ? '' : String(cell)
            return s.includes(',') || s.includes('"') || s.includes('\n')
              ? `"${s.replace(/"/g, '""')}"`
              : s
          })
          .join(',')
      )
      .join('\n')
    navigator.clipboard.writeText(`${header}\n${rowsCsv}`).catch(() => {})
  }

  return (
    <div className="mt-3">
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {result.columns.map((col, i) => (
                <th
                  key={i}
                  onClick={() => toggleSort(i)}
                  className={`px-3 py-2 text-xs font-semibold text-gray-600 cursor-pointer hover:bg-gray-100 whitespace-nowrap select-none ${
                    numericCols[i] ? 'text-right' : 'text-left'
                  }`}
                >
                  {col}{' '}
                  {sortCol === i
                    ? sortDir === 'asc'
                      ? '↑'
                      : sortDir === 'desc'
                        ? '↓'
                        : ''
                    : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {sortedRows.map((row, ri) => (
              <tr key={ri} className={ri % 2 === 1 ? 'bg-gray-50 hover:bg-gray-100' : 'hover:bg-gray-50'}>
                {row.map((cell, ci) => (
                  <td
                    key={ci}
                    className={`px-3 py-2 text-gray-700 whitespace-nowrap ${
                      numericCols[ci] ? 'text-right font-mono' : 'text-left'
                    }`}
                  >
                    {cell == null ? (
                      <span className="text-gray-400 italic">null</span>
                    ) : (
                      String(cell)
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between mt-1 px-1">
        {result.row_count > result.rows.length ? (
          <p className="text-xs text-gray-500">
            Showing {result.rows.length.toLocaleString()} of {result.row_count.toLocaleString()} rows
            {' · '}
            <span className="text-gray-400">[Download full results — Coming in Phase 2]</span>
          </p>
        ) : (
          <p className="text-xs text-gray-400">{result.row_count.toLocaleString()} rows</p>
        )}
        <button
          onClick={copyCsv}
          className="text-xs text-blue-500 hover:text-blue-700 underline"
          title="Copy visible rows as CSV"
        >
          Copy CSV
        </button>
      </div>
    </div>
  )
}
