'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Analysis } from '@/lib/api'
import VegaChart from './VegaChart'

function ResultView({ result }: { result: unknown }) {
  if (result === null || result === undefined) return null
  if (typeof result === 'object' && !Array.isArray(result)) {
    const entries = Object.entries(result as Record<string, unknown>)
    if (entries.length === 0) return null
    return (
      <table className="w-full border-collapse text-left text-xs">
        <tbody>
          {entries.map(([k, v]) => (
            <tr key={k} className="border-t border-slate-100">
              <td className="px-3 py-1.5 font-mono text-slate-600">{k}</td>
              <td className="px-3 py-1.5 text-right font-mono text-slate-800">{String(v)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    )
  }
  return (
    <pre className="overflow-auto rounded bg-slate-50 p-2 text-[11px] text-slate-700">
      {JSON.stringify(result, null, 2)}
    </pre>
  )
}

export default function AnswerBubble({ analysis }: { analysis: Analysis }) {
  if (analysis.status === 'failed') {
    return (
      <div
        data-testid="answer-failed"
        className="rounded-xl border border-amber-200 bg-amber-50 p-4 shadow-sm"
      >
        <p className="text-sm font-semibold text-amber-900">
          I couldn&apos;t complete that one — here&apos;s what I tried
        </p>
        {analysis.error_message && (
          <p className="mt-1 text-sm text-amber-800">{analysis.error_message}</p>
        )}
        {analysis.code && (
          <pre className="mt-3 overflow-auto rounded bg-amber-100/60 p-3 font-mono text-[11px] text-amber-900">
            {analysis.code}
          </pre>
        )}
        <p className="mt-2 text-xs text-amber-700">
          Try rephrasing the question and send it again.
        </p>
      </div>
    )
  }

  return (
    <div
      data-testid="answer-bubble"
      className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
    >
      <div className="prose prose-sm max-w-none text-slate-800" data-testid="answer-text">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {analysis.answer ?? ''}
        </ReactMarkdown>
      </div>

      {analysis.chart_spec && (
        <div className="rounded-lg border border-slate-100 p-2">
          <VegaChart spec={analysis.chart_spec} />
        </div>
      )}

      {analysis.result !== undefined && analysis.result !== null && (
        <details className="rounded-lg border border-slate-100">
          <summary className="cursor-pointer px-3 py-2 text-xs font-medium text-slate-600">
            Result table
          </summary>
          <div className="px-3 pb-3">
            <ResultView result={analysis.result} />
          </div>
        </details>
      )}

      <details className="rounded-lg border border-slate-100" data-testid="code-block">
        <summary className="cursor-pointer px-3 py-2 text-xs font-medium text-slate-600">
          Code it ran{' '}
          {analysis.steps_taken !== undefined && (
            <span className="text-slate-400">· {analysis.steps_taken} step(s)</span>
          )}
        </summary>
        <pre className="overflow-auto rounded-b-lg bg-slate-900 p-3 font-mono text-[11px] text-slate-100">
          {analysis.code ?? '# no code recorded'}
        </pre>
      </details>
    </div>
  )
}
