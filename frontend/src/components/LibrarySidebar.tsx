'use client'

// Phase 2 stub — clearly labelled "Coming soon" so it reads as a planned
// feature, never a bug. Becomes real in Phase 2 (GET /datasets).

const PLACEHOLDERS = ['sales_2024.csv', 'inventory.csv', 'support_tickets.csv']

export function LibrarySidebar() {
  return (
    <aside className="hidden w-64 shrink-0 lg:block">
      <div className="sticky top-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">Dataset Library</h2>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">
            Coming soon
          </span>
        </div>
        <ul className="space-y-1.5" aria-hidden="true">
          {PLACEHOLDERS.map(name => (
            <li
              key={name}
              className="flex items-center gap-2 rounded-lg border border-dashed border-slate-200 px-3 py-2 text-sm text-slate-300"
            >
              <span className="h-2 w-2 rounded-full bg-slate-200" />
              {name}
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-slate-400">
          Saved datasets and past conversations will appear here in Phase 2.
        </p>
      </div>
    </aside>
  )
}
