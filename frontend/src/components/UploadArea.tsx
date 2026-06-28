'use client'

import { useRef, useState } from 'react'
import { Spinner } from './ui'

interface UploadAreaProps {
  onFile: (file: File) => void
  uploading: boolean
  /** True once at least one dataset is loaded — switches to a compact prompt. */
  hasDataset: boolean
}

const ACCEPT = '.csv,.xlsx'

function isAllowed(file: File): boolean {
  const lower = file.name.toLowerCase()
  return lower.endsWith('.csv') || lower.endsWith('.xlsx')
}

/**
 * Drag-and-drop AND click-to-pick upload control for CSV / .xlsx files.
 * Owns its own drag highlight + local "unsupported type" hint; delegates the
 * actual upload (and its loading/error state) to the parent via `onFile`.
 */
export function UploadArea({ onFile, uploading, hasDataset }: UploadAreaProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [localHint, setLocalHint] = useState<string | null>(null)

  function handleFiles(files: FileList | null) {
    setLocalHint(null)
    const file = files?.[0]
    if (!file) return
    if (!isAllowed(file)) {
      setLocalHint(`"${file.name}" is not a CSV or .xlsx file.`)
      return
    }
    onFile(file)
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    if (uploading) return
    handleFiles(e.dataTransfer.files)
  }

  function openPicker() {
    if (uploading) return
    inputRef.current?.click()
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      openPicker()
    }
  }

  return (
    <div>
      <div
        role="button"
        tabIndex={uploading ? -1 : 0}
        aria-disabled={uploading}
        aria-label="Upload a CSV or Excel file"
        onClick={openPicker}
        onKeyDown={onKeyDown}
        onDragOver={(e) => {
          e.preventDefault()
          if (!uploading) setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={[
          'flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 text-center transition-colors',
          hasDataset ? 'py-6' : 'py-12',
          uploading ? 'cursor-wait border-slate-200 bg-slate-50' : '',
          dragging
            ? 'border-indigo-500 bg-indigo-50'
            : 'border-slate-300 bg-white hover:border-indigo-400 hover:bg-slate-50',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500',
        ].join(' ')}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          onChange={(e) => handleFiles(e.target.files)}
          disabled={uploading}
        />
        {uploading ? (
          <Spinner label="Loading & profiling your file…" />
        ) : (
          <>
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              className="mb-3 h-8 w-8 text-indigo-500"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 16V4m0 0l-4 4m4-4l4 4" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
            </svg>
            <p className="text-sm font-medium text-slate-800">
              {hasDataset ? 'Drop another file or click to replace' : 'Drop a CSV or Excel file to begin'}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              CSV or .xlsx · drag-and-drop or click to browse · try{' '}
              <code className="rounded bg-slate-100 px-1 py-0.5 text-[11px] text-slate-700">
                samples/sample_sales.csv
              </code>
            </p>
          </>
        )}
      </div>

      {localHint && (
        <p role="alert" className="mt-2 text-xs text-rose-700">
          {localHint}
        </p>
      )}
    </div>
  )
}
