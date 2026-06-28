// A clearly-labelled, NON-FUNCTIONAL "coming soon" panel.
// Visually distinct from real surfaces: dimmed, dashed border, a "Coming soon" badge,
// and a one-line description of what it will do. Reads as planned-and-pending, never as a bug.

export function StubPanel({
  title,
  phase,
  description,
}: {
  title: string
  phase: string
  description: string
}) {
  return (
    <div
      className="rounded-lg border border-dashed border-slate-300 bg-slate-100/60 p-4 opacity-80"
      aria-disabled="true"
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-500">{title}</h3>
        <span className="shrink-0 rounded-full bg-slate-200 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">
          Coming soon · {phase}
        </span>
      </div>
      <p className="mt-2 text-xs leading-relaxed text-slate-400">{description}</p>
    </div>
  )
}
