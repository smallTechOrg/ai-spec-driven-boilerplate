'use client'

import { useRef, useState } from 'react'
import { ApiError, Dataset, uploadDataset } from '@/lib/api'

// Drag-and-drop + file-picker for one CSV. On success it hands the Dataset back to the parent;
// on error it renders an inline red banner and stays usable.
export function UploadArea({
  onUploaded,
  hasDataset,
}: {
  onUploaded: (d: Dataset) => void
  hasDataset: boolean
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleFile(file: File | undefined | null) {
    if (!file) return
    setError(null)
    setUploading(true)
    try {
      const ds = await uploadDataset(file)
      onUploaded(ds)
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : 'Upload failed — please try again.'
      setError(msg)
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <section aria-label="Upload a dataset">
      <div
        role="button"
        tabIndex={0}
        onClick={() => !uploading && inputRef.current?.click()}
        onKeyDown={e => {
          if ((e.key === 'Enter' || e.key === ' ') && !uploading) {
            e.preventDefault()
            inputRef.current?.click()
          }
        }}
        onDragOver={e => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => {
          e.preventDefault()
          setDragging(false)
          if (!uploading) handleFile(e.dataTransfer.files?.[0])
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
          dragging
            ? 'border-indigo-500 bg-indigo-50'
            : 'border-slate-300 bg-white hover:border-indigo-400 hover:bg-slate-50'
        } ${uploading ? 'pointer-events-none opacity-70' : ''}`}
      >
        {uploading ? (
          <>
            <Spinner />
            <p className="mt-3 text-sm font-medium text-slate-700">Uploading and profiling…</p>
            <p className="mt-1 text-xs text-slate-400">Reading your file off the request thread.</p>
          </>
        ) : (
          <>
            <svg
              className="h-8 w-8 text-slate-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 7.5 12 3m0 0L7.5 7.5M12 3v13.5"
              />
            </svg>
            <p className="mt-3 text-sm font-medium text-slate-700">
              {hasDataset ? 'Upload a different CSV' : 'Drop a CSV here, or click to choose'}
            </p>
            <p className="mt-1 text-xs text-slate-400">CSV files up to ~100MB · one file in Phase 1</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          onChange={e => handleFile(e.target.files?.[0])}
          aria-label="Choose a CSV file"
        />
      </div>

      {error && (
        <div
          role="alert"
          className="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          <span className="font-medium">Upload failed.</span> {error}
        </div>
      )}
    </section>
  )
}

function Spinner() {
  return (
    <svg
      className="h-7 w-7 animate-spin text-indigo-500 motion-reduce:animate-none"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}
