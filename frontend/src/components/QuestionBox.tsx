'use client'

import { useState } from 'react'

interface QuestionBoxProps {
  onAsk: (question: string) => void
  /** An ask is in flight — disable the form. */
  asking: boolean
  /** No dataset loaded yet — disable with an explanatory hint. */
  disabled: boolean
  datasetName?: string
}

const EXAMPLES = [
  'What were total sales by region?',
  'Which month had the highest revenue?',
  'Show the top 5 products by quantity.',
]

/**
 * Plain-English question input + submit. Disabled until a dataset is loaded.
 * Shows a small set of example prompts to teach the feature.
 */
export function QuestionBox({ onAsk, asking, disabled, datasetName }: QuestionBoxProps) {
  const [question, setQuestion] = useState('')
  const canSubmit = !disabled && !asking && question.trim().length > 0

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    onAsk(question.trim())
  }

  return (
    <form onSubmit={submit} className="space-y-2">
      <label htmlFor="question" className="block text-sm font-medium text-slate-800">
        Ask a question{datasetName ? ` about ${datasetName}` : ''}
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          id="question"
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={disabled || asking}
          placeholder={disabled ? 'Load a file first…' : 'e.g. What were total sales by region?'}
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
        />
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {asking ? 'Asking…' : 'Ask'}
        </button>
      </div>
      {!disabled && !asking && (
        <div className="flex flex-wrap gap-1.5 pt-0.5">
          <span className="text-xs text-slate-400">Try:</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => setQuestion(ex)}
              className="rounded-full border border-slate-200 bg-white px-2.5 py-0.5 text-xs text-slate-600 transition-colors hover:border-indigo-300 hover:text-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              {ex}
            </button>
          ))}
        </div>
      )}
    </form>
  )
}
