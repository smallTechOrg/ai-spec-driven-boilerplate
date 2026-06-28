'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { AnalysisRun } from '@/lib/api'
import CodePanel from './CodePanel'
import { StubChip } from './Stub'

function formatCost(cost: number | null | undefined): string {
  if (cost === null || cost === undefined) return '—'
  if (cost === 0) return '$0.00'
  if (cost < 0.01) return `$${cost.toFixed(4)}`
  return `$${cost.toFixed(4)}`
}

export default function AnswerCard({ run }: { run: AnalysisRun }) {
  const failed = run.status === 'failed'

  return (
    <div className="space-y-3">
      {/* The user's question, echoed for context (P1 = one Q/A at a time). */}
      <div className="flex justify-end">
        <p className="max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-sm text-white shadow-sm">
          {run.question}
        </p>
      </div>

      <div
        className={[
          'rounded-2xl rounded-tl-sm border bg-white p-4 shadow-sm',
          failed ? 'border-rose-200' : 'border-slate-200',
        ].join(' ')}
      >
        {failed ? (
          <FailedBody run={run} />
        ) : (
          <div className="markdown text-sm leading-relaxed text-slate-700">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {run.answer && run.answer.trim()
                ? run.answer
                : '_The agent returned an empty answer._'}
            </ReactMarkdown>
          </div>
        )}

        {run.code && run.code.trim() && (
          <div className="mt-3">
            <CodePanel code={run.code} />
          </div>
        )}

        {/* Per-question token + cost (REAL in P1). */}
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-slate-100 pt-2.5 text-[11px] text-slate-500">
          <span className="inline-flex items-center gap-1">
            <span className="text-slate-400">tokens</span>
            <span className="font-mono font-medium text-slate-600">
              {run.tokens?.total?.toLocaleString() ?? '—'}
            </span>
            {run.tokens && (
              <span className="text-slate-400">
                ({run.tokens.prompt?.toLocaleString() ?? '?'} in /{' '}
                {run.tokens.completion?.toLocaleString() ?? '?'} out)
              </span>
            )}
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="text-slate-400">cost</span>
            <span className="font-mono font-medium text-slate-600">{formatCost(run.cost_usd)}</span>
          </span>
          <span
            className={[
              'ml-auto rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
              failed ? 'bg-rose-50 text-rose-600' : 'bg-emerald-50 text-emerald-600',
            ].join(' ')}
          >
            {failed ? 'Failed' : 'Answered'}
          </span>
        </div>

        {/* Follow-up suggestions are a P3 surface — shown as labelled stubs. */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-[11px] text-slate-400">Follow-ups:</span>
          <StubChip label="Break this down" />
          <StubChip label="Compare over time" />
        </div>
      </div>
    </div>
  )
}

function FailedBody({ run }: { run: AnalysisRun }) {
  return (
    <div>
      <div className="flex items-center gap-2">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-rose-100 text-xs font-bold text-rose-600">
          !
        </span>
        <h3 className="text-sm font-semibold text-rose-700">Couldn&apos;t compute that answer</h3>
      </div>
      <p className="mt-1.5 text-sm text-slate-600">
        {run.error_message?.trim()
          ? run.error_message
          : 'The agent ran out of attempts before it could land a reliable answer. The code it tried is shown below — try rephrasing or narrowing the question.'}
      </p>
    </div>
  )
}
