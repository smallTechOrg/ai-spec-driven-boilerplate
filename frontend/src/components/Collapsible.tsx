'use client'

import { useState } from 'react'

// A keyboard-accessible disclosure. Uses a real <button> so it is focusable and
// announced; the panel is only mounted when open.
export function Collapsible({
  label,
  children,
  defaultOpen = false,
}: {
  label: string
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="rounded-md border border-slate-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
      >
        <span>{label}</span>
        <span
          className={`text-slate-400 transition-transform ${open ? 'rotate-90' : ''}`}
          aria-hidden="true"
        >
          ▸
        </span>
      </button>
      {open && <div className="border-t border-slate-100 px-3 py-3">{children}</div>}
    </div>
  )
}
