'use client'

import { useState } from 'react'

export default function CodePanel({
  code,
  label = 'Show code',
  defaultOpen = false,
}: {
  code: string
  label?: string
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  const [copied, setCopied] = useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 bg-slate-50 px-3 py-2 text-left text-xs font-medium text-slate-600 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-400"
      >
        <span className="flex items-center gap-1.5">
          <Chevron open={open} />
          {label}
        </span>
        <span className="font-mono text-[10px] uppercase tracking-wide text-slate-400">pandas</span>
      </button>
      {open && (
        <div className="relative bg-slate-900">
          <button
            type="button"
            onClick={copy}
            className="absolute right-2 top-2 z-10 rounded border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            {copied ? 'Copied' : 'Copy'}
          </button>
          <pre className="overflow-x-auto p-3 pr-16 text-xs leading-relaxed text-slate-100">
            <code className="font-mono whitespace-pre">{code}</code>
          </pre>
        </div>
      )}
    </div>
  )
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-90' : ''} motion-reduce:transition-none`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="9 18 15 12 9 6" />
    </svg>
  )
}
