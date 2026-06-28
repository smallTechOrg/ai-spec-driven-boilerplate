import { StubBadge } from './StubBadge'

interface FollowUpsProps {
  followUps: string[]
}

/**
 * Suggested follow-up questions, rendered as chips. DISPLAY-ONLY in Phase 1:
 * click-to-ask is wired in Phase 4, so the section is labelled "preview" and the
 * chips are visibly non-interactive (cursor-default, no hover affordance) with a
 * tooltip — they must never read as broken buttons.
 */
export function FollowUps({ followUps }: FollowUpsProps) {
  if (!followUps || followUps.length === 0) return null
  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Suggested follow-ups
        </h4>
        <StubBadge phase="Phase 4" />
      </div>
      <div className="flex flex-wrap gap-2">
        {followUps.map((q, i) => (
          <span
            key={i}
            title="Click-to-ask coming soon (Phase 4)"
            aria-disabled="true"
            className="cursor-default select-none rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-500"
          >
            {q}
          </span>
        ))}
      </div>
      <p className="mt-1.5 text-[11px] text-slate-400">Preview — clicking to re-ask arrives in Phase 4.</p>
    </div>
  )
}
