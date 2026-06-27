'use client'

import { useState } from 'react'
import type { AskStep } from '@/lib/api'

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }
  return (
    <button
      type="button"
      onClick={copy}
      className="rounded px-1.5 py-0.5 text-[10px] font-medium text-gray-400 hover:bg-gray-700 hover:text-gray-100"
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}

const RESULT_PREVIEW_CHARS = 3000

function StepResult({ text, isError }: { text: string; isError: boolean }) {
  const [expanded, setExpanded] = useState(false)
  const isTruncated = text.length > RESULT_PREVIEW_CHARS
  const display = isTruncated && !expanded ? text.slice(0, RESULT_PREVIEW_CHARS) : text

  return (
    <div>
      <pre
        className={`overflow-x-auto whitespace-pre-wrap break-words px-3 py-2 font-mono text-[11px] leading-relaxed ${
          isError ? 'text-red-700' : 'text-gray-600'
        }`}
      >
        {display}
        {isTruncated && !expanded && <span className="text-gray-400">…</span>}
      </pre>
      {isTruncated && (
        <button
          type="button"
          onClick={() => setExpanded(e => !e)}
          className="px-3 pb-2 text-[10px] font-medium text-blue-600 hover:text-blue-800"
        >
          {expanded ? 'Show less' : `Show full result (${text.length.toLocaleString()} chars)`}
        </button>
      )}
    </div>
  )
}

/**
 * Agent steps inspector (C23) — collapsible.
 *
 * Lists each ReAct step: the `action` (the pandas the agent ran) in a dark code
 * block, then its `result` or error text. Error steps get a red "Error" badge.
 * Collapsed by default so the answer stays the focus; the toggle exposes the
 * full reasoning trace.
 */
export function StepsInspector({ steps }: { steps: AskStep[] }) {
  const [open, setOpen] = useState(false)

  if (!steps || steps.length === 0) return null

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-600 hover:text-gray-900"
      >
        <span aria-hidden="true">{open ? '▾' : '▸'}</span>
        Steps inspector
        <span className="rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] font-semibold text-gray-500">
          {steps.length}
        </span>
      </button>

      {open && (
        <ol className="mt-2 space-y-2" aria-label="Agent steps">
          {steps.map((step, i) => (
            <li key={i} className="rounded-md border border-gray-200">
              {/* Action — dark code block with inline header */}
              <div className="overflow-hidden rounded-t-md bg-gray-900">
                <div className="flex items-center justify-between border-b border-gray-700 px-3 py-1">
                  <span className="text-[11px] font-medium text-gray-400">Step {i + 1}</span>
                  <div className="flex items-center gap-1.5">
                    {step.is_error && (
                      <span className="rounded bg-red-900 px-1.5 py-0.5 text-[10px] font-semibold text-red-300">
                        Error
                      </span>
                    )}
                    <CopyButton text={step.action} />
                  </div>
                </div>
                <pre className="overflow-x-auto px-3 py-2 font-mono text-[11px] leading-relaxed text-gray-100">
                  <code>{step.action}</code>
                </pre>
              </div>

              {/* Result / error text — guarded against large frame output */}
              {step.result && (
                <StepResult text={step.result} isError={!!step.is_error} />
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
