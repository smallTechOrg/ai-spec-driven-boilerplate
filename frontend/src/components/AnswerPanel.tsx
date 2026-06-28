'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { AskResponse } from '@/lib/api'
import { Collapsible } from './Collapsible'

// Renders one completed assistant answer: markdown answer text, a "Chart coming soon" badge
// (charts are P3), collapsible plan / code / result preview, and clickable follow-up chips.
export function AnswerPanel({
  answer,
  onSuggestion,
}: {
  answer: AskResponse
  onSuggestion: (q: string) => void
}) {
  return (
    <div className="space-y-3">
      <div className="prose prose-sm max-w-none text-slate-800 prose-pre:bg-slate-900 prose-pre:text-slate-100">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer.answer}</ReactMarkdown>
      </div>

      {/* Charts are a Phase 3 surface — labelled stub inline so it never reads as missing. */}
      <div className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-slate-300 bg-slate-100/70 px-2.5 py-1 text-[11px] font-medium text-slate-400">
        <span aria-hidden="true">📊</span> Chart coming soon · P3
      </div>

      <div className="space-y-2">
        {answer.plan && (
          <Collapsible label="Show plan">
            <div className="prose prose-sm max-w-none text-slate-700">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer.plan}</ReactMarkdown>
            </div>
          </Collapsible>
        )}

        {answer.code && (
          <Collapsible label="Show code">
            <pre className="overflow-auto rounded-md bg-slate-900 p-3 text-xs leading-relaxed text-slate-100">
              <code className="font-mono">{answer.code}</code>
            </pre>
          </Collapsible>
        )}

        {answer.result_preview && (
          <Collapsible label="Show result preview">
            <pre className="overflow-auto rounded-md border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-700">
              <code className="font-mono">{answer.result_preview}</code>
            </pre>
          </Collapsible>
        )}
      </div>

      {answer.suggestions && answer.suggestions.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-medium text-slate-400">Suggested follow-ups</p>
          <div className="flex flex-wrap gap-2">
            {answer.suggestions.map((s, i) => (
              <button
                key={`${i}-${s}`}
                type="button"
                onClick={() => onSuggestion(s)}
                className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 transition-colors hover:bg-indigo-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
