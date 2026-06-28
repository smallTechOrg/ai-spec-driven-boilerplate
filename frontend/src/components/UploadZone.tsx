'use client'

import { useRef, useState } from 'react'

interface Props {
  onUpload: (file: File) => void
  loading: boolean
  error: string | null
}

export function UploadZone({ onUpload, loading, error }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function pick(files: FileList | null) {
    const file = files?.[0]
    if (file) onUpload(file)
  }

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload a CSV file"
        aria-disabled={loading}
        onClick={() => !loading && inputRef.current?.click()}
        onKeyDown={e => {
          if ((e.key === 'Enter' || e.key === ' ') && !loading) {
            e.preventDefault()
            inputRef.current?.click()
          }
        }}
        onDragOver={e => {
          e.preventDefault()
          if (!loading) setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => {
          e.preventDefault()
          setDragging(false)
          if (!loading) pick(e.dataTransfer.files)
        }}
        className={[
          'flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition focus:outline-none focus:ring-2 focus:ring-indigo-500',
          dragging
            ? 'border-indigo-500 bg-indigo-50'
            : 'border-slate-300 bg-white hover:border-indigo-400 hover:bg-slate-50',
          loading ? 'pointer-events-none opacity-60' : '',
        ].join(' ')}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={e => pick(e.target.files)}
        />
        {loading ? (
          <div className="flex flex-col items-center gap-3">
            <Spinner />
            <p className="text-sm font-medium text-slate-700">Profiling your dataset…</p>
            <p className="text-xs text-slate-500">Reading every row locally — raw data stays on your machine.</p>
          </div>
        ) : (
          <>
            <svg className="mb-3 h-10 w-10 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
            </svg>
            <p className="text-base font-semibold text-slate-800">Drop a CSV here, or click to choose</p>
            <p className="mt-1 text-sm text-slate-500">Up to ~100MB. We profile it locally and never send raw rows to the model.</p>
          </>
        )}
      </div>
      {error && (
        <div role="alert" className="mt-3 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <svg className="mt-0.5 h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m0 3.75h.008M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
          <span><strong className="font-semibold">Upload failed.</strong> {error}</span>
        </div>
      )}
    </div>
  )
}

export function Spinner({ className = 'h-6 w-6 text-indigo-500' }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}
