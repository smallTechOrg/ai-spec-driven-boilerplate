'use client'

import { useRef, useState } from 'react'
import { uploadDataset, ApiError, type DatasetBundle } from '@/lib/api'

const ACCEPT = '.csv,.tsv,.xls,.xlsx'
const MAX_BYTES = 100 * 1024 * 1024 // ~100MB, matches the API limit.

type Phase = 'idle' | 'uploading' | 'profiling'

function looksSupported(file: File): boolean {
  return /\.(csv|tsv|xls|xlsx)$/i.test(file.name)
}

export default function Upload({
  onUploaded,
}: {
  onUploaded: (bundle: DatasetBundle) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [phase, setPhase] = useState<Phase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const [activeName, setActiveName] = useState<string | null>(null)

  const busy = phase !== 'idle'

  async function handleFile(file: File) {
    setError(null)
    if (!looksSupported(file)) {
      setError('Unsupported file type. Upload a CSV, TSV, or Excel (.xls/.xlsx) file.')
      return
    }
    if (file.size > MAX_BYTES) {
      setError('That file is larger than the ~100MB limit.')
      return
    }
    setActiveName(file.name)
    setPhase('uploading')
    try {
      // The single POST does upload + profiling server-side; we surface a
      // distinct "profiling" beat once bytes are likely sent so the wait reads
      // as real work rather than a frozen screen.
      const profilingTimer = setTimeout(() => setPhase('profiling'), 600)
      const bundle = await uploadDataset(file)
      clearTimeout(profilingTimer)
      onUploaded(bundle)
      setPhase('idle')
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? e.message
          : 'Could not reach the server. Is it running on this machine?'
      setError(msg)
      setPhase('idle')
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    if (busy) return
    const file = e.dataTransfer.files?.[0]
    if (file) void handleFile(file)
  }

  return (
    <div>
      <div
        onDragOver={e => {
          e.preventDefault()
          if (!busy) setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={[
          'rounded-xl border-2 border-dashed p-5 text-center transition-colors',
          dragging
            ? 'border-indigo-400 bg-indigo-50'
            : 'border-slate-300 bg-white hover:border-slate-400',
          busy ? 'opacity-80' : '',
        ].join(' ')}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          disabled={busy}
          onChange={e => {
            const file = e.target.files?.[0]
            if (file) void handleFile(file)
            e.target.value = '' // allow re-selecting the same file
          }}
        />
        {busy ? (
          <div className="flex flex-col items-center gap-2 py-2 text-sm text-slate-600">
            <Spinner />
            <span className="font-medium">
              {phase === 'uploading' ? 'Uploading' : 'Profiling'} {activeName ?? 'file'}…
            </span>
            <span className="text-xs text-slate-400">
              {phase === 'uploading'
                ? 'Sending the file to your local server.'
                : 'Reading columns, dtypes and ranges. Raw rows stay on your machine.'}
            </span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 py-1">
            <UploadIcon />
            <p className="text-sm font-medium text-slate-700">
              Drop a spreadsheet here, or
            </p>
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1"
            >
              Choose a file
            </button>
            <p className="text-xs text-slate-400">CSV, TSV or Excel · up to ~100MB</p>
          </div>
        )}
      </div>

      {error && (
        <div
          role="alert"
          className="mt-3 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700"
        >
          <span aria-hidden="true" className="mt-0.5 font-bold">!</span>
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}

function Spinner() {
  return (
    <span
      className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-600 motion-reduce:animate-none"
      aria-hidden="true"
    />
  )
}

function UploadIcon() {
  return (
    <svg
      className="h-7 w-7 text-slate-400"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  )
}
