'use client'

import { ComingSoonBadge } from './ComingSoon'

// Top navigation. "Analyze" is the only real tab in Phase 1.
// "Dashboards" is a labelled, non-interactive stub for Phase 4.
// "Senior analyst mode" is a disabled stub toggle for Phase 5.
export function TopNav() {
  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-3 px-6 py-3">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-blue-600 text-sm font-bold text-white">
            DA
          </span>
          <span className="text-base font-semibold tracking-tight text-gray-900">
            Local Data Analyst
          </span>
        </div>

        <nav className="flex items-center gap-1" aria-label="Primary">
          <span
            aria-current="page"
            className="rounded-md bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700"
          >
            Analyze
          </span>
          <button
            type="button"
            disabled
            aria-disabled="true"
            title="Dashboards — Coming soon (Phase 4)"
            className="flex cursor-not-allowed items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium text-gray-400"
          >
            Dashboards
            <ComingSoonBadge />
          </button>
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <span className="text-sm text-gray-400">Senior analyst mode</span>
          {/* Disabled stub switch — Phase 5 */}
          <span
            role="switch"
            aria-checked="false"
            aria-disabled="true"
            title="Senior analyst mode — Coming soon (Phase 5)"
            className="relative inline-flex h-5 w-9 cursor-not-allowed items-center rounded-full bg-gray-200"
          >
            <span className="ml-0.5 h-4 w-4 rounded-full bg-white shadow" />
          </span>
          <ComingSoonBadge />
        </div>
      </div>
    </header>
  )
}
