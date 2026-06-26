'use client'

import { StubPill, StubNote } from '@/components/StubBanner'
import type { LastQueryTokens } from '@/components/analyse/AnalyseTab'

/**
 * Token usage widget (C18) — partly REAL in Phase 2.
 *
 * The "Last query (In / Out)" row is wired to the most recent answer's token
 * counts (passed down from the Conversation card). The provider/mode line
 * reflects GET /health. The daily totals, cost table, storage row, and the
 * C29 token-budget bar remain labelled stubs — /stats/daily and pricing arrive
 * in a later phase — so they show "—" with a clear "coming soon" note rather
 * than looking broken.
 */
export function TokenWidget({
  provider,
  lastTokens,
}: {
  provider?: string
  lastTokens: LastQueryTokens | null
}) {
  const mode =
    provider === 'stub'
      ? 'Stub (offline)'
      : provider
        ? provider
        : '—'

  const lastQuery = lastTokens
    ? `${lastTokens.input} / ${lastTokens.output}`
    : '— / —'

  return (
    <section
      aria-labelledby="tokens-heading"
      className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 id="tokens-heading" className="text-sm font-semibold text-gray-800">
          Token usage
        </h2>
      </div>

      {/* Real rows (Phase 2) */}
      <dl className="space-y-1.5 text-xs">
        <Row label="Provider / mode" value={mode} live />
        <Row label="Last query (In / Out)" value={lastQuery} live={!!lastTokens} />
      </dl>

      {/* Stubbed rows (daily stats + cost + storage) */}
      <div className="mt-3 border-t border-gray-100 pt-3">
        <div className="mb-1.5 flex items-center justify-between gap-2">
          <span className="text-[11px] font-medium text-gray-500">Daily stats &amp; cost</span>
          <StubPill phase={3} />
        </div>
        <dl className="space-y-1.5 text-xs">
          <Row label="Today (In / Out / Queries)" value="— / — / —" />
          <Row label="Today cost" value="—" />
          <Row label="Storage (datasets / rows)" value="—" />
        </dl>
        <StubNote>
          Daily totals, per-query cost, and the context-budget bar arrive in a
          later phase.
        </StubNote>
      </div>
    </section>
  )
}

function Row({
  label,
  value,
  live = false,
}: {
  label: string
  value: string
  live?: boolean
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-gray-500">{label}</dt>
      <dd
        className={`font-medium tabular-nums ${live ? 'text-gray-800' : 'text-gray-400'}`}
      >
        {value}
      </dd>
    </div>
  )
}
