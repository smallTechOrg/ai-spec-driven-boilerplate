'use client'

import { useRef, useState } from 'react'

interface Props {
  onFile: (file: File) => void
  uploading: boolean
  error: string | null
}

export default function UploadZone({ onFile, uploading, error }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function pick(file?: File | null) {
    if (file) onFile(file)
  }

  return (
    <div className="mx-auto max-w-xl text-center">
      <div
        onDragOver={e => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => {
          e.preventDefault()
          setDragging(false)
          pick(e.dataTransfer.files?.[0])
        }}
        className={`rounded-2xl border-2 border-dashed p-10 transition-colors ${
          dragging ? 'border-indigo-400 bg-indigo-50' : 'border-slate-300 bg-white'
        }`}
      >
        <p className="text-base font-semibold text-slate-800">Upload a CSV to begin</p>
        <p className="mt-1 text-sm text-slate-500">
          Drag a file here, or pick one. Your rows stay on this machine.
        </p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="mt-5 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-50"
        >
          {uploading ? 'Profiling…' : 'Choose CSV'}
        </button>
        <input
          ref={inputRef}
          data-testid="file-input"
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={e => pick(e.target.files?.[0])}
        />
      </div>

      {uploading && (
        <div
          data-testid="upload-loading"
          className="mt-4 flex items-center justify-center gap-2 text-sm text-slate-500"
        >
          <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-500" />
          Profiling your dataset…
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
        >
          {error}
        </div>
      )}
    </div>
  )
}
