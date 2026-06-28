'use client'

// Phase 3 stubs — disabled action buttons with a visible "Coming soon" badge
// and a tooltip, so they read as planned features, never broken controls.

const ACTIONS = [
  { label: 'Compare datasets', tip: 'Join and compare multiple datasets — coming in a later phase.' },
  { label: 'Save cleaned dataset', tip: 'Save a derived/cleaned dataset back to your library — coming in a later phase.' },
  { label: 'Upload Excel', tip: 'Excel & multi-sheet workbooks — coming in a later phase.' },
]

export function StubActions() {
  return (
    <div className="flex flex-wrap gap-2">
      {ACTIONS.map(({ label, tip }) => (
        <button
          key={label}
          type="button"
          disabled
          title={tip}
          aria-disabled="true"
          className="inline-flex cursor-not-allowed items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm font-medium text-slate-400"
        >
          {label}
          <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-slate-500">
            Soon
          </span>
        </button>
      ))}
    </div>
  )
}
