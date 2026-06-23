'use client'

import type { Session } from '../lib/api'

interface Props {
  sessions: Session[]
  activeSessionId: string | null
  onSelect: (sessionId: string) => void
  onCreate: () => void
  loading: boolean
}

export default function SessionSidebar({
  sessions,
  activeSessionId,
  onSelect,
  onCreate,
  loading,
}: Props) {
  return (
    <div className="h-full flex flex-col bg-gray-900 text-white w-64 shrink-0">
      <div className="p-4 border-b border-gray-700">
        <h1 className="text-lg font-semibold">Data Analyst</h1>
      </div>
      <div className="p-3">
        <button
          onClick={onCreate}
          disabled={loading}
          className="w-full rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          + New Session
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {sessions.length === 0 && (
          <p className="text-xs text-gray-500 px-2 py-4 text-center">
            No sessions yet.
            <br />
            Click &quot;New Session&quot; to start.
          </p>
        )}
        {sessions.map((s) => (
          <button
            key={s.session_id}
            onClick={() => onSelect(s.session_id)}
            className={`w-full text-left rounded-lg px-3 py-2 text-sm truncate transition-colors ${
              s.session_id === activeSessionId
                ? 'bg-blue-700 text-white'
                : 'text-gray-300 hover:bg-gray-700'
            }`}
            title={s.name}
          >
            <span className="block truncate">{s.name}</span>
            {(s.dataset_count !== undefined || s.message_count !== undefined) && (
              <span className="text-xs text-gray-400">
                {s.dataset_count ?? 0} datasets · {s.message_count ?? 0} messages
              </span>
            )}
          </button>
        ))}
      </div>
      <div className="p-3 border-t border-gray-700">
        <p className="text-xs text-gray-500 text-center">
          Rename/Delete sessions — Phase 2
        </p>
      </div>
    </div>
  )
}
