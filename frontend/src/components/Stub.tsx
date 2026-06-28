// Visible-but-non-functional placeholders. Phase 1 renders the full product
// vision; surfaces not yet wired are shown here in a clearly disabled
// "Coming soon" state so the user sees the roadmap and never mistakes an
// unbuilt feature for a bug.

export function ComingSoonBadge({ phase = 'Soon' }: { phase?: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
      <span className="h-1.5 w-1.5 rounded-full bg-slate-400" aria-hidden="true" />
      Coming soon{phase && phase !== 'Soon' ? ` · ${phase}` : ''}
    </span>
  )
}

export function StubCard({
  title,
  description,
  phase,
  children,
}: {
  title: string
  description: string
  phase?: string
  children?: React.ReactNode
}) {
  return (
    <section
      aria-disabled="true"
      className="select-none rounded-xl border border-dashed border-slate-300 bg-slate-50/60 p-4 opacity-75"
    >
      <header className="mb-1.5 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-500">{title}</h3>
        <ComingSoonBadge phase={phase} />
      </header>
      <p className="text-xs leading-relaxed text-slate-400">{description}</p>
      {children && <div className="mt-3 text-slate-300">{children}</div>}
    </section>
  )
}

// An inline, smaller stub for chips/toggles inside otherwise-real cards.
export function StubChip({ label }: { label: string }) {
  return (
    <span
      aria-disabled="true"
      title="Coming soon"
      className="inline-flex cursor-not-allowed items-center gap-1 rounded-full border border-dashed border-slate-300 bg-slate-50 px-2.5 py-1 text-xs text-slate-400"
    >
      {label}
      <span className="text-[9px] font-semibold uppercase tracking-wide text-slate-400">soon</span>
    </span>
  )
}
