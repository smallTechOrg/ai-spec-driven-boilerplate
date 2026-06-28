'use client'

import { formatCost } from '@/lib/api'

interface Props {
  sessionCost: number
  sessionTokens: number
}

export function Header({ sessionCost, sessionTokens }: Props) {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-3">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">DA</span>
          <div>
            <h1 className="text-base font-bold leading-tight text-slate-900">Data Analyst</h1>
            <p className="text-[11px] leading-tight text-slate-500">Local-first · code runs on your machine · raw data never leaves</p>
          </div>
        </div>

        {/* Header cost: session total is REAL; multi-day history is a Phase-2 stub. */}
        <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5">
          <div className="text-right">
            <div className="text-sm font-semibold tabular-nums text-slate-800">
              {formatCost(sessionCost)}
              <span className="ml-1 text-xs font-normal text-slate-400">/ {sessionTokens.toLocaleString()} tok</span>
            </div>
            <div className="text-[10px] text-slate-400">
              session total · <span className="italic">daily history coming soon</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
