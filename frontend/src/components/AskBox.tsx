'use client'

import { useState } from 'react'

export default function AskBox({
  disabled,
  busy,
  onAsk,
}: {
  disabled: boolean
  busy: boolean
  onAsk: (question: string) => void
}) {
  const [value, setValue] = useState('')
  const canSend = !disabled && !busy && value.trim().length > 0

  function submit() {
    if (!canSend) return
    onAsk(value.trim())
    setValue('')
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter submits; Shift+Enter inserts a newline.
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <form
      onSubmit={e => {
        e.preventDefault()
        submit()
      }}
      className="rounded-xl border border-slate-200 bg-white p-2 shadow-sm focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-100"
    >
      <label htmlFor="ask" className="sr-only">
        Ask a question about your dataset
      </label>
      <div className="flex items-end gap-2">
        <textarea
          id="ask"
          rows={1}
          value={value}
          disabled={disabled || busy}
          onChange={e => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={
            disabled
              ? 'Upload a dataset to start asking questions…'
              : 'Ask anything — e.g. “What is the total revenue by region?”'
          }
          className="max-h-40 min-h-[2.5rem] flex-1 resize-none bg-transparent px-2 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={!canSend}
          className="mb-0.5 inline-flex h-9 items-center gap-1.5 rounded-lg bg-indigo-600 px-4 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? 'Analyzing…' : 'Ask'}
        </button>
      </div>
      <p className="px-2 pb-1 pt-0.5 text-[11px] text-slate-400">
        Enter to send · Shift+Enter for a new line · your rows never leave this machine
      </p>
    </form>
  )
}
