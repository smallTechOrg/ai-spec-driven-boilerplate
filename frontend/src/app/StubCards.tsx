'use client'

/**
 * Labelled non-functional placeholders for features that are not built in Phase 1.
 *
 * Two distinct visual languages on purpose:
 *  - "Coming soon" cards (Charts / Anomalies): greyed-out + a coloured "Coming in Phase N"
 *    badge. They read as work-in-progress, not bugs.
 *  - "Not planned" card (Connect a database): a muted, struck-through, dashed-border
 *    style so the user understands it is intentionally excluded, never just pending.
 */

function ComingSoonCard({
  title,
  description,
  badge,
  preview,
}: {
  title: string
  description: string
  badge: string
  preview: React.ReactNode
}) {
  return (
    <div
      aria-disabled="true"
      className="relative cursor-not-allowed select-none rounded-xl border border-gray-200 bg-gray-50 p-5 opacity-70"
      title="Coming soon — not available yet"
    >
      <span className="absolute right-4 top-4 rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">
        {badge}
      </span>
      <h3 className="pr-28 text-base font-semibold text-gray-500">{title}</h3>
      <p className="mt-1 text-sm text-gray-400">{description}</p>
      <div className="pointer-events-none mt-4 rounded-lg border border-dashed border-gray-300 bg-white/60 p-4">
        {preview}
      </div>
    </div>
  )
}

export function ChartsStub() {
  return (
    <ComingSoonCard
      title="Charts & visual summaries"
      description="Ask for a chart in plain English and see it rendered locally."
      badge="Coming in Phase 2"
      preview={
        <div className="flex h-24 items-end gap-2" aria-hidden="true">
          {[40, 70, 30, 90, 55, 65].map((h, i) => (
            <div
              key={i}
              style={{ height: `${h}%` }}
              className="flex-1 rounded-t bg-gray-300"
            />
          ))}
        </div>
      }
    />
  )
}

export function AnomaliesStub() {
  return (
    <ComingSoonCard
      title="Automatic patterns & anomalies"
      description="One click to surface outliers, missing data, and notable relationships."
      badge="Coming in Phase 3"
      preview={
        <ul className="space-y-2" aria-hidden="true">
          {[0, 1, 2].map(i => (
            <li key={i} className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-gray-300" />
              <span className="h-3 flex-1 rounded bg-gray-200" />
            </li>
          ))}
        </ul>
      }
    />
  )
}

export function DatabaseStub() {
  return (
    <div
      aria-disabled="true"
      className="relative cursor-not-allowed select-none rounded-xl border border-dashed border-gray-300 bg-gray-100 p-5"
      title="Not planned — this tool works with CSV files only"
    >
      <span className="absolute right-4 top-4 rounded-full border border-gray-300 bg-white px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide text-gray-400">
        Not planned
      </span>
      <h3 className="pr-28 text-base font-semibold text-gray-400 line-through decoration-gray-300">
        Connect a database
      </h3>
      <p className="mt-1 text-sm text-gray-400">
        Out of scope — this tool works with CSV files only.
      </p>
    </div>
  )
}
