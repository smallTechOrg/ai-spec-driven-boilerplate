'use client'

import { useState, useRef } from 'react'
import type { Dataset } from '../lib/api'
import { uploadDataset } from '../lib/api'

interface Props {
  sessionId: string
  datasets: Dataset[]
  onDatasetAdded: (dataset: Dataset) => void
}

export default function DatasetPanel({ sessionId, datasets, onDatasetAdded }: Props) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFile(file: File) {
    setError(null)
    setUploading(true)
    try {
      const dataset = await uploadDataset(sessionId, file)
      onDatasetAdded(dataset)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
      // Reset the file input so the same file can be re-uploaded after an error
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <div className="border-b border-gray-200 bg-gray-50 p-4">
      <h2 className="text-sm font-semibold text-gray-700 mb-3">Datasets</h2>

      {/* Upload zone */}
      <div
        onClick={() => !uploading && inputRef.current?.click()}
        onDrop={onDrop}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors mb-3 ${
          dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'
        } ${uploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click() }}
        aria-label="Upload dataset file"
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.json"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) handleFile(f)
          }}
          disabled={uploading}
        />
        {uploading ? (
          <p className="text-sm text-blue-600">Uploading...</p>
        ) : (
          <>
            <p className="text-sm text-gray-500">Drop a CSV, Excel, or JSON file here</p>
            <p className="text-xs text-gray-400 mt-1">or click to browse</p>
          </>
        )}
      </div>

      {error && (
        <div className="mb-3 rounded bg-red-50 border border-red-200 p-2 text-xs text-red-700">
          Upload failed: {error}. Try again.
        </div>
      )}

      {/* Dataset list */}
      {datasets.length > 0 && (
        <div className="space-y-1">
          {datasets.map((d) => (
            <div
              key={d.dataset_id}
              className="flex items-center justify-between rounded-lg bg-white border border-gray-200 px-3 py-2"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate">{d.name}</p>
                <p className="text-xs text-gray-500">
                  {d.row_count.toLocaleString()} rows · {d.columns.length} columns
                </p>
              </div>
              <span className="ml-2 shrink-0 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                Ready
              </span>
            </div>
          ))}
        </div>
      )}

      {datasets.length === 0 && (
        <p className="text-xs text-gray-400 text-center py-2">No datasets uploaded yet</p>
      )}
    </div>
  )
}
