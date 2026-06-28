'use client'

interface FollowUpsStripProps {
  followups: string[]
  onPick: (question: string) => void
  disabled?: boolean
}

/**
 * Real Suggested-follow-ups strip (Phase 2 — replaces FollowUpsStub).
 * Renders the 2–3 follow-up questions from the run's `final` event as
 * clickable chips. Clicking one submits it as a new question via `onPick`
 * (the same path QuestionBox uses), kicking off a fresh analysis.
 *
 * Renders nothing when there are no suggestions, so the surface stays clean.
 */
export default function FollowUpsStrip({ followups, onPick, disabled }: FollowUpsStripProps) {
  if (!followups || followups.length === 0) return null

  return (
    <section
      aria-label="Suggested follow-ups"
      data-testid="followups-strip"
      className="rounded-lg border border-gray-200 bg-gray-50/60 p-4"
    >
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Suggested follow-ups
      </h3>
      <div className="flex flex-wrap gap-2">
        {followups.map((q) => (
          <button
            key={q}
            type="button"
            data-testid="followup-chip"
            disabled={disabled}
            onClick={() => !disabled && onPick(q)}
            className="cursor-pointer rounded-full border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm transition-colors hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-gray-300 disabled:hover:bg-white disabled:hover:text-gray-700"
          >
            {q}
          </button>
        ))}
      </div>
    </section>
  )
}
