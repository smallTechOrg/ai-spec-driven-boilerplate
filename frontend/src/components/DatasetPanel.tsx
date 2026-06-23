'use client'

import { useRef, useState } from 'react'
import type { Dataset } from '../lib/api'
import { ComingSoonBadge } from './ComingSoon'

export function DatasetPanel({
  dataset,
  uploading,
  error,
  onUpload,
}: {
  dataset: Dataset | null
  uploading: boolean
  error: string | null
  onUpload: (file: File) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  function pick() {
    inputRef.current?.click()
  }

  function handleFile(file: File | undefined) {
    if (file) onUpload(file)
  }

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">Dataset</h2>
        <span className="text-[11px] text-gray-400">CSV only · Phase 1</span>
      </div>

      {/* Drop zone / file picker */}
      <div
        onDragOver={e => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => {
          e.preventDefault()
          setDragOver(false)
          if (!uploading) handleFile(e.dataTransfer.files?.[0])
        }}
        className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-6 text-center transition ${
          dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 bg-gray-50'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          aria-label="Upload CSV file"
          disabled={uploading}
          onChange={e => {
            handleFile(e.target.files?.[0])
            e.target.value = ''
          }}
        />
        <p className="text-sm text-gray-600">
          {uploading ? 'Uploading and ingesting…' : 'Drag a CSV here or'}
        </p>
        <button
          type="button"
          onClick={pick}
          disabled={uploading}
          className="mt-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {uploading ? 'Working…' : dataset ? 'Replace with another CSV' : 'Choose a CSV file'}
        </button>
      </div>

      {error && (
        <p className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}

      {!dataset && !error && !uploading && (
        <p className="mt-3 text-sm text-gray-500">
          Upload a CSV to begin. It becomes a queryable local table — your data never leaves this
          machine.
        </p>
      )}

      {dataset && (
        <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="text-base font-semibold text-gray-900">{dataset.name}</span>
            <code className="rounded bg-gray-200 px-1.5 py-0.5 font-mono text-xs text-gray-700">
              {dataset.table_name}
            </code>
            <span className="text-sm text-gray-500">{dataset.row_count.toLocaleString()} rows</span>
          </div>

          <p className="mt-3 text-[11px] font-semibold uppercase tracking-wide text-gray-400">
            Detected columns ({dataset.columns.length})
          </p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {dataset.columns.map(col => (
              <span
                key={col.name}
                className="inline-flex items-center gap-1.5 rounded-md border border-gray-200 bg-white px-2 py-1 text-xs"
              >
                <span className="font-medium text-gray-800">{col.name}</span>
                <span className="rounded bg-gray-100 px-1 font-mono text-[10px] uppercase text-gray-500">
                  {col.type}
                </span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Multi-dataset manager — labelled stub for Phase 2 */}
      <div className="mt-4 rounded-lg border border-dashed border-gray-300 bg-gray-50/70 p-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-gray-400">Manage multiple datasets</span>
          <ComingSoonBadge />
        </div>
        <p className="mt-1 text-[11px] text-gray-400">
          Upload, rename, switch and query across several datasets — Phase 2.
        </p>
      </div>
    </section>
  )
}
