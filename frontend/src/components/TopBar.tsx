import { StubBadge } from './StubBadge'

interface TopBarProps {
  /** The most recent query's estimated USD cost, if any (real). */
  lastCostUsd: number | null
}

/** App header with the title and a daily-cost-total stub. */
export function TopBar({ lastCostUsd }: TopBarProps) {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-2.5">
          <span
            aria-hidden="true"
            className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white"
          >
            DA
          </span>
          <div>
            <h1 className="text-base font-semibold leading-tight text-slate-900">
              Local Data Analyst
            </h1>
            <p className="text-[11px] leading-tight text-slate-500">
              Your data stays on this machine — only schema &amp; aggregates reach the model.
            </p>
          </div>
        </div>

        {/* Daily-cost total — STUB (Phase 5), shows last query's cost as real context */}
        <div className="flex items-center gap-2 rounded-lg border border-dashed border-slate-200 bg-slate-50/60 px-3 py-1.5">
          <div className="text-right">
            <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
              Last query cost
            </p>
            <p className="text-sm font-semibold text-slate-700">
              {lastCostUsd === null ? '—' : `$${lastCostUsd.toFixed(5)}`}
            </p>
          </div>
          <div className="h-8 w-px bg-slate-200" />
          <div className="flex flex-col items-start gap-0.5">
            <span className="text-[11px] text-slate-400">Daily total</span>
            <StubBadge phase="Phase 5" />
          </div>
        </div>
      </div>
    </header>
  )
}
