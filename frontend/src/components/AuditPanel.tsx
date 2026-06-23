'use client'

import { useState } from 'react'
import type { AuditEntry } from '../lib/api'

function formatTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString()
}

function AuditRow({ entry }: { entry: AuditEntry }) {
  const [open, setOpen] = useState(false)
  const isIngest = entry.operation === 'ingest'
  return (
    <li className="rounded-lg border border-gray-200 bg-white p-3 text-xs shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
            isIngest ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
          }`}
        >
          {entry.operation}
        </span>
        <span
          className={`inline-flex items-center gap-1 text-[11px] font-medium ${
            entry.success ? 'text-green-600' : 'text-red-600'
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              entry.success ? 'bg-green-500' : 'bg-red-500'
            }`}
          />
          {entry.success ? 'Success' : 'Error'}
        </span>
        <span className="ml-auto text-[11px] text-gray-400">{formatTime(entry.created_at)}</span>
      </div>

      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-500">
        {entry.row_count != null && (
          <span>
            <span className="font-medium text-gray-700">{entry.row_count}</span> rows
          </span>
        )}
        {entry.duration_ms != null && (
          <span>
            <span className="font-medium text-gray-700">{entry.duration_ms}</span> ms
          </span>
        )}
        {entry.columns && entry.columns.length > 0 && (
          <span>
            <span className="font-medium text-gray-700">{entry.columns.length}</span> cols
          </span>
        )}
      </div>

      {entry.error_message && (
        <p className="mt-2 rounded border border-red-200 bg-red-50 px-2 py-1 text-[11px] text-red-700">
          {entry.error_message}
        </p>
      )}

      {entry.sql_text && (
        <div className="mt-2">
          <button
            type="button"
            onClick={() => setOpen(o => !o)}
            className="text-[11px] font-medium text-blue-600 hover:text-blue-700"
            aria-expanded={open}
          >
            {open ? 'Hide SQL' : 'Show SQL'}
          </button>
          {open && (
            <pre className="mt-1 overflow-x-auto rounded bg-gray-900 p-2 font-mono text-[11px] leading-relaxed text-gray-100">
              {entry.sql_text}
            </pre>
          )}
        </div>
      )}
    </li>
  )
}

export function AuditPanel({
  entries,
  loading,
  error,
}: {
  entries: AuditEntry[]
  loading: boolean
  error: string | null
}) {
  return (
    <aside className="flex h-full flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">Audit trail</h2>
        <span className="text-[11px] text-gray-400">Every data operation</span>
      </div>

      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
          {error}
        </p>
      )}

      {!error && loading && entries.length === 0 && (
        <p className="rounded-lg border border-gray-200 bg-white p-3 text-xs text-gray-400">
          Loading audit trail…
        </p>
      )}

      {!error && !loading && entries.length === 0 && (
        <p className="rounded-lg border border-dashed border-gray-300 bg-white p-3 text-xs text-gray-400">
          No operations yet. Upload a dataset or run a query and it appears here.
        </p>
      )}

      {entries.length > 0 && (
        <ul className="flex flex-col gap-2 overflow-y-auto pr-1">
          {entries.map(e => (
            <AuditRow key={e.id} entry={e} />
          ))}
        </ul>
      )}
    </aside>
  )
}
