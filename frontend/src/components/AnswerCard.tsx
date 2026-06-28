'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { formatCost, type AnswerData } from '@/lib/api'
import { ResultChart } from './ResultChart'
import { ResultTable } from './ResultTable'
import { StepStatusBar, type StepMap } from './StepStatus'
import { Spinner } from './UploadZone'

export interface Turn {
  id: string
  question: string
  status: 'running' | 'done' | 'error'
  steps: StepMap
  answer: AnswerData | null
  error: string | null
}

interface Props {
  turn: Turn
  onFollowUp: (q: string) => void
  asking: boolean
}

export function AnswerCard({ turn, onFollowUp, asking }: Props) {
  const [showCode, setShowCode] = useState(false)
  const [showPlan, setShowPlan] = useState(false)
  const a = turn.answer

  return (
    <article className="rounded-xl border border-slate-200 bg-white shadow-sm">
      {/* user question */}
      <div className="flex items-start gap-3 border-b border-slate-100 px-5 py-3">
        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-semibold text-white">You</span>
        <p className="text-sm font-medium text-slate-800">{turn.question}</p>
      </div>

      <div className="space-y-4 px-5 py-4">
        {/* live step status */}
        {(turn.status === 'running' || turn.status === 'error') && (
          <StepStatusBar steps={turn.steps} />
        )}

        {/* error */}
        {turn.status === 'error' && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <strong className="font-semibold">The agent couldn&apos;t answer this.</strong>
            <p className="mt-1">{turn.error}</p>
            {a?.code && (
              <pre className="mt-2 overflow-x-auto rounded bg-red-100/60 p-2 font-mono text-xs text-red-800">{a.code}</pre>
            )}
          </div>
        )}

        {/* running skeleton */}
        {turn.status === 'running' && !a && (
          <div className="flex items-center gap-3 text-sm text-slate-500">
            <Spinner className="h-4 w-4 text-indigo-500" />
            Working on it — generating and running code locally…
          </div>
        )}

        {/* answer */}
        {a && turn.status !== 'error' && (
          <>
            {a.assumptions && a.assumptions.length > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
                <strong className="font-semibold">Assumptions:</strong>
                <ul className="ml-4 list-disc">
                  {a.assumptions.map((x, i) => <li key={i}>{x}</li>)}
                </ul>
              </div>
            )}

            <div className="prose prose-sm prose-slate max-w-none text-slate-800">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{a.answer}</ReactMarkdown>
            </div>

            {a.chart_spec && a.result_table?.length > 0 && (
              <ResultChart spec={a.chart_spec} rows={a.result_table} />
            )}

            {a.result_table?.length > 0 && <ResultTable rows={a.result_table} />}

            {/* disclosures */}
            <div className="flex flex-wrap gap-2">
              {a.code && (
                <Disclosure label="code" open={showCode} onToggle={() => setShowCode(v => !v)} />
              )}
              {a.plan?.length > 0 && (
                <Disclosure label="plan" open={showPlan} onToggle={() => setShowPlan(v => !v)} />
              )}
            </div>

            {showCode && a.code && (
              <pre className="overflow-x-auto rounded-lg border border-slate-200 bg-slate-900 p-4 font-mono text-xs leading-relaxed text-slate-100">{a.code}</pre>
            )}
            {showPlan && a.plan?.length > 0 && (
              <ol className="ml-5 list-decimal space-y-1 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                {a.plan.map((step, i) => <li key={i}>{step}</li>)}
              </ol>
            )}

            {/* follow-up chips */}
            {a.follow_ups?.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <span className="text-xs font-medium text-slate-400">Try next:</span>
                {a.follow_ups.map((q, i) => (
                  <button
                    key={i}
                    type="button"
                    disabled={asking}
                    onClick={() => onFollowUp(q)}
                    className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 transition hover:bg-indigo-100 focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-50"
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}

            {/* cost line */}
            <div className="flex items-center gap-4 border-t border-slate-100 pt-3 text-xs text-slate-500">
              <span title="tokens (prompt + completion)">
                {a.token_usage.total.toLocaleString()} tokens
                <span className="text-slate-400"> ({a.token_usage.prompt.toLocaleString()} in / {a.token_usage.completion.toLocaleString()} out)</span>
              </span>
              <span className="font-medium text-slate-600">{formatCost(a.estimated_cost_usd)}</span>
            </div>
          </>
        )}
      </div>
    </article>
  )
}

function Disclosure({ label, open, onToggle }: { label: string; open: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={open}
      className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
    >
      <svg className={`h-3 w-3 transition-transform ${open ? 'rotate-90' : ''}`} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <path fillRule="evenodd" d="M7.3 4.3a1 1 0 0 1 1.4 0l5 5a1 1 0 0 1 0 1.4l-5 5a1 1 0 0 1-1.4-1.4L11.6 10 7.3 5.7a1 1 0 0 1 0-1.4Z" clipRule="evenodd" />
      </svg>
      {open ? `Hide ${label}` : `Show ${label}`}
    </button>
  )
}
