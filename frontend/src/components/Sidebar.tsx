'use client'

// Left sidebar: active dataset + clearly-labelled non-functional stubs. Every stub is
// greyed, non-interactive, and tagged "Coming soon" so it is never mistaken for a bug.

const STUBS: { label: string; hint: string }[] = [
  { label: 'Multi-file & dataset switcher', hint: 'Load and compare several files' },
  { label: 'Folder as one source', hint: 'Point at a directory of CSVs' },
  { label: 'Saved sessions & history', hint: 'Resume work across days' },
  { label: 'Column annotations', hint: 'Describe columns for the agent' },
  { label: 'Derived-dataset library', hint: 'Save cleaned results' },
  { label: 'Follow-up suggestions', hint: 'Suggested next questions' },
  { label: 'Tokens & cost', hint: 'Per-query cost + daily total' },
  { label: 'External SQL source', hint: 'Connect a read-only database' },
  { label: 'Excel (.xlsx) upload', hint: 'Beyond CSV' },
]

export default function Sidebar({ datasetName }: { datasetName: string | null }) {
  return (
    <aside className="flex w-72 shrink-0 flex-col gap-4 border-r border-slate-200 bg-slate-50 p-4">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
          Active dataset
        </p>
        <p
          data-testid="active-dataset"
          className="mt-1 truncate font-mono text-sm text-slate-800"
          title={datasetName ?? undefined}
        >
          {datasetName ?? 'None yet — upload a CSV'}
        </p>
      </div>

      <div className="flex-1">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
          Coming soon
        </p>
        <ul className="space-y-1.5">
          {STUBS.map(stub => (
            <li
              key={stub.label}
              aria-disabled="true"
              className="cursor-not-allowed select-none rounded-lg border border-slate-200 bg-white/60 px-3 py-2 opacity-60"
              title={`${stub.hint} — coming soon`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-xs font-medium text-slate-500">
                  {stub.label}
                </span>
                <span className="shrink-0 rounded bg-slate-200 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-slate-500">
                  Soon
                </span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  )
}
