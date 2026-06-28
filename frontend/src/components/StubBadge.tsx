// Shared "Coming soon" treatment for not-yet-built features.
//
// Phase 1 ships visually-complete UI: the working path is real, and everything
// arriving in a later phase is shown as a clearly-LABELLED, visibly-disabled
// stub so the user sees the vision without mistaking a stub for a bug.

interface StubBadgeProps {
  /** Which phase this feature lands in, e.g. "Phase 2". */
  phase: string
}

/** A small muted pill reading "Coming soon · <phase>". */
export function StubBadge({ phase }: StubBadgeProps) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-slate-400" />
      Coming soon · {phase}
    </span>
  )
}

interface StubCardProps {
  title: string
  phase: string
  description: string
  children?: React.ReactNode
}

/**
 * A muted, non-interactive card that previews a future feature. The whole card
 * is visibly disabled (reduced opacity, no pointer events on its controls) and
 * carries a StubBadge so it never reads as broken.
 */
export function StubCard({ title, phase, description, children }: StubCardProps) {
  return (
    <section
      aria-label={`${title} (coming soon)`}
      className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 p-4"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-500">{title}</h3>
        <StubBadge phase={phase} />
      </div>
      <p className="mt-1 text-xs leading-relaxed text-slate-400">{description}</p>
      {children && <div className="mt-3 select-none opacity-60">{children}</div>}
    </section>
  )
}
