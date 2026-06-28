import type { AskCost } from '../lib/api'

interface CostBadgeProps {
  cost: AskCost
}

function fmtUsd(usd: number): string {
  // Show enough precision for sub-cent costs.
  if (usd < 0.01) return `$${usd.toFixed(5)}`
  return `$${usd.toFixed(4)}`
}

/** Per-query token + estimated USD cost for an answer. */
export function CostBadge({ cost }: CostBadgeProps) {
  const total = cost.prompt_tokens + cost.completion_tokens
  return (
    <div className="inline-flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-600">
      <span className="font-medium text-slate-700">Query cost</span>
      <span>
        {cost.prompt_tokens.toLocaleString()} prompt + {cost.completion_tokens.toLocaleString()}{' '}
        completion = {total.toLocaleString()} tokens
      </span>
      <span className="font-semibold text-slate-800">{fmtUsd(cost.est_usd)}</span>
    </div>
  )
}
