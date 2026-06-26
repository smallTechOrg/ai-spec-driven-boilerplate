'use client'

import { useRef, useState } from 'react'
import { DatasetResponse, uploadDataset } from '@/lib/api'

interface FilePanelProps {
  sessionId: string
  datasets: DatasetResponse[]
  activeDatasetId: string | null
  onDatasetUploaded: (dataset: DatasetResponse) => void
  onSelectDataset: (datasetId: string) => void
}

export function FilePanel({
  sessionId,
  datasets,
  activeDatasetId,
  onDatasetUploaded,
  onSelectDataset,
}: FilePanelProps) {
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setUploadError('Only .csv files are supported.')
      return
    }
    if (file.size > 50 * 1024 * 1024) {
      setUploadError('File too large. Maximum size is 50 MB.')
      return
    }
    setUploadError(null)
    setUploading(true)
    try {
      const ds = await uploadDataset(sessionId, file)
      onDatasetUploaded(ds)
    } catch (err: unknown) {
      setUploadError(
        err instanceof Error ? `Upload failed: ${err.message}` : 'Upload failed.',
      )
    } finally {
      setUploading(false)
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    e.target.value = ''
  }

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Files</h2>

      {/* Upload dropzone */}
      <div
        className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
          dragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
        } ${uploading ? 'opacity-60 cursor-not-allowed' : ''}`}
        onClick={() => !uploading && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        role="button"
        aria-label="Upload CSV file"
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={handleChange}
          disabled={uploading}
        />
        {uploading ? (
          <div className="flex items-center justify-center gap-2 text-sm text-blue-600">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Uploading…
          </div>
        ) : (
          <div className="text-sm text-gray-500">
            <span className="text-blue-600 font-medium">Click to upload</span> or drag &amp; drop
            <p className="text-xs mt-1">.csv files only</p>
          </div>
        )}
      </div>

      {uploadError && <p className="text-xs text-red-600 mt-1">{uploadError}</p>}

      {/* File list */}
      {datasets.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-gray-500 font-medium">Uploaded files</p>
          {datasets.map((ds) => (
            <button
              key={ds.dataset_id}
              onClick={() => onSelectDataset(ds.dataset_id)}
              className={`text-left rounded-lg border p-3 transition-colors ${
                activeDatasetId === ds.dataset_id
                  ? 'border-blue-500 bg-blue-50 text-blue-800'
                  : 'border-gray-200 bg-white hover:border-blue-300'
              }`}
            >
              <p className="text-sm font-medium truncate">{ds.filename}</p>
              <p className="text-xs text-gray-500">
                {ds.row_count.toLocaleString()} rows · {ds.column_names.length} columns
              </p>
            </button>
          ))}
        </div>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Phase 3 stub — always visible, clearly labelled, non-interactive */}
      <div className="rounded-lg border border-dashed border-amber-300 bg-amber-50 p-3">
        <p className="text-xs font-medium text-amber-700">Multi-file queries coming in Phase 3</p>
        <p className="text-xs text-amber-600 mt-0.5">— not yet active</p>
      </div>
    </div>
  )
}
