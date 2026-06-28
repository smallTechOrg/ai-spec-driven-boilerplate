'use client'

import type { Dataset, DatasetBundle } from '@/lib/api'
import Upload from './Upload'
import { ComingSoonBadge } from './Stub'

export default function Library({
  active,
  onUploaded,
}: {
  active: Dataset | null
  onUploaded: (bundle: DatasetBundle) => void
}) {
  return (
    <div className="flex h-full flex-col gap-5">
      <div>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Add data
        </h2>
        <Upload onUploaded={onUploaded} />
      </div>

      <div>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          This session
        </h2>
        {active ? (
          <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-3">
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded bg-indigo-600 text-[10px] font-bold uppercase text-white">
                {active.kind?.slice(0, 3) || 'csv'}
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-800" title={active.name}>
                  {active.name}
                </p>
                <p className="text-[11px] text-slate-500">
                  {active.row_count.toLocaleString()} rows · {active.column_count} cols
                </p>
              </div>
            </div>
          </div>
        ) : (
          <p className="rounded-lg border border-dashed border-slate-200 bg-white px-3 py-4 text-center text-xs text-slate-400">
            No dataset yet. Upload one to begin.
          </p>
        )}
      </div>

      {/* Persistent multi-day library is a P2 surface. */}
      <div className="opacity-75">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Library
          </h2>
          <ComingSoonBadge phase="P2" />
        </div>
        <ul className="space-y-1.5" aria-disabled="true">
          {['quarterly_sales.xlsx', 'support_tickets.csv', 'inventory_2025.csv'].map(name => (
            <li
              key={name}
              className="flex cursor-not-allowed items-center gap-2 rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-2"
            >
              <span className="h-6 w-6 shrink-0 rounded bg-slate-200" aria-hidden="true" />
              <span className="truncate text-xs text-slate-400">{name}</span>
            </li>
          ))}
        </ul>
        <p className="mt-1.5 text-[11px] text-slate-400">
          Your datasets will persist across days and restarts.
        </p>
      </div>

      {/* Multi-file / folder picker is a P4 surface. */}
      <div className="mt-auto opacity-75">
        <button
          type="button"
          disabled
          aria-disabled="true"
          className="flex w-full cursor-not-allowed items-center justify-between rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-400"
        >
          <span>+ Combine multiple files / folder</span>
          <ComingSoonBadge phase="P4" />
        </button>
      </div>
    </div>
  )
}
