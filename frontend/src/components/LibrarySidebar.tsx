import type { Dataset } from '../lib/api'
import { StubBadge, StubCard } from './StubBadge'

interface LibrarySidebarProps {
  /** The currently-loaded dataset, if any (real). */
  current: Dataset | null
}

/**
 * Left rail. In Phase 1 it shows the currently-loaded dataset as real context,
 * plus clearly-LABELLED "Coming soon" previews of the library, session restore,
 * watched folder, and multi-file join — each visibly disabled so it is never
 * mistaken for a broken feature.
 */
export function LibrarySidebar({ current }: LibrarySidebarProps) {
  return (
    <aside className="space-y-4">
      {/* Active dataset — REAL */}
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-900">Active dataset</h3>
        </div>
        {current ? (
          <div className="mt-2 rounded-lg border border-indigo-200 bg-indigo-50/60 px-3 py-2">
            <p className="truncate text-sm font-medium text-slate-900" title={current.name}>
              {current.name}
            </p>
            <p className="text-xs text-slate-500">
              {current.row_count.toLocaleString()} rows · {current.profile.columns.length} cols
            </p>
          </div>
        ) : (
          <p className="mt-2 text-xs text-slate-400">No dataset loaded yet.</p>
        )}
      </section>

      {/* Library list — STUB (Phase 2) */}
      <StubCard
        title="Library"
        phase="Phase 2"
        description="Loaded datasets will persist here so you can switch between them. Add, select, and delete arrive next."
      >
        <ul className="space-y-1.5">
          {['quarterly_revenue.xlsx', 'customers.csv', 'orders_2025.csv'].map((name) => (
            <li
              key={name}
              className="flex items-center justify-between rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-500"
            >
              <span className="truncate">{name}</span>
              <span className="text-slate-300">switch</span>
            </li>
          ))}
        </ul>
      </StubCard>

      {/* Session restore — STUB (Phase 2) */}
      <StubCard
        title="Resume previous session"
        phase="Phase 2"
        description="Your datasets and Q&A history will restore across days, so you pick up where you left off."
      >
        <button
          type="button"
          disabled
          aria-disabled="true"
          className="w-full cursor-not-allowed rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-400"
        >
          Restore last session
        </button>
      </StubCard>

      {/* Multi-file join — STUB (Phase 3) */}
      <StubCard
        title="Join datasets"
        phase="Phase 3"
        description="Combine two datasets or treat a folder of like files as one, and ask across them."
      >
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="flex-1 rounded-md border border-slate-200 bg-white px-2 py-1.5">orders</span>
          <span>⋈</span>
          <span className="flex-1 rounded-md border border-slate-200 bg-white px-2 py-1.5">customers</span>
        </div>
      </StubCard>

      {/* Watched folder — STUB (Phase 4) */}
      <StubCard
        title="Watch a folder"
        phase="Phase 4"
        description="Point at a local folder and dropped files are auto-ingested into your library."
      >
        <div className="flex items-center gap-2">
          <input
            type="text"
            disabled
            placeholder="/path/to/watched/folder"
            className="flex-1 cursor-not-allowed rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-400 placeholder:text-slate-300"
          />
          <span className="rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-300">
            Watch
          </span>
        </div>
      </StubCard>

      {/* Re-run history — STUB (Phase 5) */}
      <StubCard
        title="Reproducible re-run"
        phase="Phase 5"
        description="Re-run any past query from your audit history with one click and reproduce the exact answer."
      >
        <div className="flex items-center justify-between rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-400">
          <span className="truncate">Total sales by region</span>
          <span className="inline-flex items-center gap-1">
            Re-run <StubBadge phase="Phase 5" />
          </span>
        </div>
      </StubCard>
    </aside>
  )
}
