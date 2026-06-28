'use client'

import { useState } from 'react'
import type { Dataset } from '../lib/api'

interface CodePanelProps {
  generatedSql: string
  planSteps: string[]
  dataset: Dataset
}

/**
 * Expandable "Code / Steps / Profile" disclosure — collapsed by default.
 * Expands to show the exact DuckDB SQL that ran, the plan steps, and the
 * dataset profile, so the user can inspect and trust the answer.
 */
export function CodePanel({ generatedSql, planSteps, dataset }: CodePanelProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-lg border border-slate-200">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 rounded-lg px-4 py-3 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
      >
        <span>Code / Steps / Profile</span>
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          className={`h-4 w-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {open && (
        <div className="space-y-5 border-t border-slate-200 px-4 py-4">
          <section>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Plan steps
            </h4>
            {planSteps.length > 0 ? (
              <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-700">
                {planSteps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            ) : (
              <p className="text-sm text-slate-400">No plan steps were recorded.</p>
            )}
          </section>

          <section>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Generated DuckDB SQL
            </h4>
            {generatedSql ? (
              <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs leading-relaxed text-slate-100">
                <code>{generatedSql}</code>
              </pre>
            ) : (
              <p className="text-sm text-slate-400">No SQL was generated.</p>
            )}
          </section>

          <section>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Dataset profile
            </h4>
            <p className="mb-2 text-xs text-slate-500">
              {dataset.name} · {dataset.profile.row_count.toLocaleString()} rows ·{' '}
              {dataset.profile.columns.length} columns
            </p>
            <div className="flex flex-wrap gap-1.5">
              {dataset.profile.columns.map((col) => (
                <span
                  key={col.name}
                  className="inline-flex items-center gap-1 rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs text-slate-600"
                >
                  {col.name}
                  <span className="text-slate-400">{col.type}</span>
                </span>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
