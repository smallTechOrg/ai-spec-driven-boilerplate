'use client'

import { useRef, useState } from 'react'
import { uploadFile, UploadedFile } from '@/lib/api'

interface UploadZoneProps {
  onSuccess: (file: UploadedFile) => void
}

export function UploadZone({ onSuccess }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
    const file = files[0]
    if (!file.name.endsWith('.csv')) {
      setError('Only CSV files are supported in Phase 1.')
      return
    }
    setError(null)
    setLoading(true)
    try {
      const uploaded = await uploadFile(file)
      onSuccess(uploaded)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed.')
    } finally {
      setLoading(false)
      // Reset input so the same file can be re-uploaded
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  function onDragOver(e: React.DragEvent) {
    e.preventDefault()
    setDragging(true)
  }

  function onDragLeave() {
    setDragging(false)
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  return (
    <div className="space-y-2">
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`
          cursor-pointer rounded-lg border-2 border-dashed p-4 text-center text-sm transition-colors
          ${dragging
            ? 'border-blue-400 bg-blue-50'
            : 'border-gray-300 bg-white hover:border-blue-300 hover:bg-blue-50'
          }
        `}
      >
        {loading ? (
          <div className="flex flex-col items-center gap-2 text-gray-500">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500" />
            <span>Uploading...</span>
          </div>
        ) : (
          <>
            <div className="text-2xl mb-1">+</div>
            <p className="font-medium text-gray-700">Upload CSV</p>
            <p className="text-gray-400 text-xs mt-1">Drag & drop or click to browse</p>
          </>
        )}
      </div>

      {/* Hidden file input — required for Playwright setInputFiles */}
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />

      {error && (
        <p className="text-xs text-red-600 rounded bg-red-50 border border-red-200 px-2 py-1">
          {error}
        </p>
      )}
    </div>
  )
}
