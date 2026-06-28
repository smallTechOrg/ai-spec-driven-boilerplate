'use client'

import { useState } from 'react'
import { UploadedFile } from '@/lib/api'

interface SchemaPreviewProps {
  file: UploadedFile
}

export function SchemaPreview({ file }: SchemaPreviewProps) {
  const [expanded, setExpanded] = useState(false)
  const { schema_preview, row_count } = file

  return (
    <div className="mt-2 text-xs">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-gray-500 hover:text-gray-700"
      >
        <span>{expanded ? '▼' : '▶'}</span>
        <span>
          {schema_preview.columns.length} columns
          {row_count != null ? `, ${row_count.toLocaleString()} rows` : ''}
        </span>
      </button>

      {expanded && (
        <div className="mt-2 overflow-auto rounded border border-gray-200 bg-white">
          <table className="min-w-full text-xs">
            <thead className="bg-gray-50">
              <tr>
                {schema_preview.columns.map((col) => (
                  <th
                    key={col}
                    className="px-2 py-1 text-left font-medium text-gray-600 border-b border-gray-200 whitespace-nowrap"
                  >
                    {col}
                    <span className="ml-1 font-normal text-gray-400">
                      ({schema_preview.dtypes[col] ?? 'unknown'})
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {schema_preview.sample_rows.map((row, rowIdx) => (
                <tr key={rowIdx} className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  {row.map((cell, colIdx) => (
                    <td
                      key={colIdx}
                      className="px-2 py-1 text-gray-700 border-b border-gray-100 whitespace-nowrap"
                    >
                      {cell == null ? <span className="text-gray-300">null</span> : String(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
