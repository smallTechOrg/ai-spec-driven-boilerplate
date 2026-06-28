import type { KeyStat } from '../lib/api'

interface KeyStatsProps {
  stats: KeyStat[]
}

function fmtValue(value: string | number): string {
  if (typeof value === 'number') return value.toLocaleString(undefined, { maximumFractionDigits: 4 })
  return value
}

/** Key-stat callouts rendered as a responsive grid of cards. */
export function KeyStats({ stats }: KeyStatsProps) {
  if (stats.length === 0) return null
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {stats.map((stat, i) => (
        <div
          key={`${stat.label}-${i}`}
          className="rounded-lg border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-3"
        >
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{stat.label}</p>
          <p className="mt-1 text-xl font-semibold text-slate-900">
            {fmtValue(stat.value)}
            {stat.unit ? <span className="ml-1 text-sm font-normal text-slate-500">{stat.unit}</span> : null}
          </p>
        </div>
      ))}
    </div>
  )
}
