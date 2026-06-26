'use client'

/**
 * Stub-mode primitives for the Data Analysis Agent shell.
 *
 *  - <StubBanner provider /> : the yellow "stub mode" banner. From Phase 2 it is
 *      driven by GET /health's `provider`: shown ONLY when the backend runs in
 *      stub mode (no API key) so canned answers are never mistaken for real.
 *  - <StubPill />  : a small "Phase N — not yet wired" tag reused on every
 *      placeholder control that is still a labelled stub.
 *  - <StubNote />  : a plain-words "coming in a later phase" note.
 */

export function StubBanner({ provider }: { provider?: string | null }) {
  // While health is loading, `provider` is undefined — render nothing (no
  // flash of a banner that may not apply). In real (gemini/openrouter) mode,
  // render nothing. Only the stub provider gets the yellow banner.
  if (provider !== 'stub') return null

  return (
    <div
      role="status"
      className="border-b border-yellow-300 bg-yellow-100 px-4 py-2 text-center text-sm text-yellow-900"
    >
      <span className="font-semibold">Stub mode</span> — no LLM API key is set, so
      the agent returns plausible canned answers and runs fully offline. Add{' '}
      <code className="rounded bg-yellow-200/70 px-1 py-0.5 text-xs">
        AGENT_GEMINI_API_KEY
      </code>{' '}
      to <code className="rounded bg-yellow-200/70 px-1 py-0.5 text-xs">.env</code> for
      real analysis.
    </div>
  )
}

export function StubPill({ phase = 2, label }: { phase?: number; label?: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-yellow-300 bg-yellow-50 px-2 py-0.5 text-[11px] font-medium whitespace-nowrap text-yellow-800">
      <span aria-hidden="true">●</span>
      {label ?? `Phase ${phase} — not yet wired`}
    </span>
  )
}

/**
 * A standardised "coming in a later phase" note. Use under a placeholder
 * control to spell out, in plain words, that it does nothing yet.
 */
export function StubNote({ children }: { children: React.ReactNode }) {
  return <p className="mt-1 text-xs text-gray-400">{children}</p>
}
