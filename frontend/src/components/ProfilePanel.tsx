'use client'

import type { ColumnProfile, Dataset, TypeCategory } from '@/lib/api'

interface ProfilePanelProps {
  dataset: Dataset
}

// Tailwind classes per type-category badge. Kept explicit (not interpolated)
// so the JIT compiler sees every literal class name.
const BADGE: Record<TypeCategory, string> = {
  numeric: 'bg-blue-50 text-blue-700 border-blue-200',
  datetime: 'bg-purple-50 text-purple-700 border-purple-200',
  categorical: 'bg-amber-50 text-amber-700 border-amber-200',
  text: 'bg-gray-100 text-gray-600 border-gray-200',
  boolean: 'bg-emerald-50 text-emerald-700 border-emerald-200',
}

const RANGED: TypeCategory[] = ['numeric', 'datetime']

/** Compact stringification for min/max/example cells. */
function display(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') {
    // Trim long floats so wide tables stay scannable.
    return Number.isInteger(value) ? String(value) : value.toFixed(3).replace(/\.?0+$/, '')
  }
  const s = String(value)
  return s.length > 24 ? `${s.slice(0, 24)}…` : s
}

/**
 * Real per-column auto-profile (Phase 2). Renders a scannable table of
 * type / distinct / missing / range / examples. Falls back to a plain
 * column list when `dataset.profile` is null/absent so a profiling
 * failure on the backend never looks like a broken UI.
 */
export default function ProfilePanel({ dataset }: ProfilePanelProps) {
  const profile = dataset.profile

  // Degraded fallback: backend profiling failed → plain column list.
  if (!profile || profile.length === 0) {
    return (
      <section
        aria-label="Column profile"
        data-testid="profile-panel"
        className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">Column profile</h2>
          <span className="text-xs text-gray-400">{dataset.schema.length} columns</span>
        </div>
        <p className="mb-3 text-xs text-gray-400">
          Detailed profiling wasn&apos;t available for this file — showing columns only.
        </p>
        <ul className="flex flex-wrap gap-1.5" data-testid="profile-fallback">
          {dataset.schema.map((col) => (
            <li
              key={col.name}
              className="rounded-md border border-gray-200 bg-gray-50 px-2 py-1 text-xs text-gray-700"
              title={col.dtype}
            >
              {col.name}
              <span className="ml-1 text-gray-400">{col.dtype}</span>
            </li>
          ))}
        </ul>
      </section>
    )
  }

  const withMissing = profile.filter((c) => c.missing > 0).length

  return (
    <section
      aria-label="Column profile"
      data-testid="profile-panel"
      className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-gray-900">Column profile</h2>
        <span className="text-xs text-gray-400">
          {profile.length} columns
          {withMissing > 0 && (
            <>
              {' · '}
              <span className="font-medium text-amber-600">{withMissing} with missing values</span>
            </>
          )}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-left text-xs">
          <thead>
            <tr className="border-b border-gray-200 text-[11px] uppercase tracking-wide text-gray-400">
              <th className="py-2 pr-3 font-medium">Column</th>
              <th className="py-2 pr-3 font-medium">Type</th>
              <th className="py-2 pr-3 text-right font-medium">Distinct</th>
              <th className="py-2 pr-3 text-right font-medium">Missing</th>
              <th className="py-2 pr-3 font-medium">Range</th>
              <th className="py-2 font-medium">Examples</th>
            </tr>
          </thead>
          <tbody>
            {profile.map((col) => (
              <ProfileRow key={col.name} col={col} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function ProfileRow({ col }: { col: ColumnProfile }) {
  const ranged = RANGED.includes(col.type_category)
  const examples = (col.examples ?? []).slice(0, 3)

  return (
    <tr className="border-b border-gray-100 last:border-0 align-top" data-testid="profile-row">
      <td className="py-2 pr-3 font-medium text-gray-900">
        <span title={col.dtype}>{col.name}</span>
      </td>
      <td className="py-2 pr-3">
        <span
          data-testid="profile-type-badge"
          className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${
            BADGE[col.type_category] ?? BADGE.text
          }`}
        >
          {col.type_category}
        </span>
      </td>
      <td className="py-2 pr-3 text-right tabular-nums text-gray-700">
        {col.distinct.toLocaleString()}
      </td>
      <td className="py-2 pr-3 text-right tabular-nums">
        {col.missing > 0 ? (
          <span className="font-medium text-amber-600">{col.missing.toLocaleString()}</span>
        ) : (
          <span className="text-gray-400">0</span>
        )}
      </td>
      <td className="py-2 pr-3 text-gray-600">
        {ranged && (col.min !== null || col.max !== null) ? (
          <span className="font-mono text-[11px]">
            {display(col.min)} – {display(col.max)}
          </span>
        ) : (
          <span className="text-gray-300">—</span>
        )}
      </td>
      <td className="py-2 text-gray-500">
        {examples.length > 0 ? (
          <span className="flex flex-wrap gap-1">
            {examples.map((ex, i) => (
              <span
                key={i}
                className="rounded border border-gray-200 bg-gray-50 px-1.5 py-0.5 font-mono text-[11px] text-gray-600"
              >
                {display(ex)}
              </span>
            ))}
          </span>
        ) : (
          <span className="text-gray-300">—</span>
        )}
      </td>
    </tr>
  )
}
