'use client'

import { useCallback, useId, useRef, useState } from 'react'
import { api, ApiError, type UploadResponse } from '@/lib/api'

/**
 * Upload card (C1, C11, C17) — REAL in Phase 2.
 *
 * A real file picker (click or drag-drop) → POST /upload, with an optional
 * shared context note sent as the `context` form field. Each file gets a row
 * showing its state: uploading / done / error, plus inline duplicate handling.
 *
 * On a 409 `duplicate_dataset` the row offers "Use existing" (dismiss) or
 * "Upload anyway" (re-POST with ?force=true). On any success the parent is
 * notified so the Tables list refreshes.
 *
 * Folder drop, per-file typed notes, notes-file attachment, and the staged
 * editable queue (C13/C16) remain for Phase 3 — this card does the core
 * single-context upload path.
 */

type FileState = 'uploading' | 'done' | 'error' | 'duplicate'

interface FileRow {
  id: string
  name: string
  state: FileState
  message?: string
  result?: UploadResponse
}

const ACCEPT = '.csv,.tsv,.txt,.json,.xlsx,.xls'

let rowSeq = 0
function nextRowId(): string {
  rowSeq += 1
  return `f${rowSeq}-${Date.now()}`
}

export function UploadCard({ onUploaded }: { onUploaded: () => void }) {
  const [context, setContext] = useState('')
  const [rows, setRows] = useState<FileRow[]>([])
  const [dragActive, setDragActive] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const contextId = useId()

  // Keep the original File objects keyed by row id so a duplicate row can be
  // re-uploaded with ?force=true (FileList is not retained across renders).
  const fileCacheRef = useRef<Map<string, File>>(new Map())

  const updateRow = useCallback((id: string, patch: Partial<FileRow>) => {
    setRows(prev => prev.map(r => (r.id === id ? { ...r, ...patch } : r)))
  }, [])

  // Upload a single file; `force` re-POSTs after a duplicate prompt.
  const doUpload = useCallback(
    async (rowId: string, file: File, force: boolean) => {
      updateRow(rowId, { state: 'uploading', message: undefined })
      try {
        const result = await api.upload(file, { context, force })
        updateRow(rowId, {
          state: 'done',
          message: `${result.row_count} rows × ${result.col_count} cols`,
          result,
        })
        fileCacheRef.current.delete(rowId)
        onUploaded()
      } catch (err) {
        if (err instanceof ApiError && err.code === 'duplicate_dataset') {
          updateRow(rowId, {
            state: 'duplicate',
            message: 'A dataset with the same content already exists.',
          })
        } else {
          const message = err instanceof Error ? err.message : 'Upload failed.'
          updateRow(rowId, { state: 'error', message })
        }
      }
    },
    [context, onUploaded, updateRow],
  )

  const startFiles = useCallback(
    (files: FileList | File[]) => {
      const list = Array.from(files)
      if (list.length === 0) return
      const newRows: FileRow[] = list.map(f => ({
        id: nextRowId(),
        name: f.name,
        state: 'uploading' as const,
      }))
      // Stash each File so a duplicate can be force-uploaded later.
      newRows.forEach((r, i) => fileCacheRef.current.set(r.id, list[i]))
      setRows(prev => [...newRows, ...prev])
      // Kick off each upload (the API helper handles multipart).
      list.forEach((file, i) => {
        void doUpload(newRows[i].id, file, false)
      })
    },
    [doUpload],
  )

  const onInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) startFiles(e.target.files)
      // Reset so picking the same file again re-fires change.
      e.target.value = ''
    },
    [startFiles],
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragActive(false)
      if (e.dataTransfer?.files?.length) startFiles(e.dataTransfer.files)
    },
    [startFiles],
  )

  const forceUpload = useCallback(
    (rowId: string) => {
      const file = fileCacheRef.current.get(rowId)
      if (file) void doUpload(rowId, file, true)
    },
    [doUpload],
  )

  const dismissRow = useCallback((rowId: string) => {
    setRows(prev => prev.filter(r => r.id !== rowId))
    fileCacheRef.current.delete(rowId)
  }, [])

  return (
    <section
      aria-labelledby="upload-heading"
      className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 id="upload-heading" className="text-sm font-semibold text-gray-800">
          Upload data
        </h2>
      </div>

      {/* Drop zone (also click-to-pick) */}
      <div
        onDragOver={e => {
          e.preventDefault()
          setDragActive(true)
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        className={`flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors ${
          dragActive
            ? 'border-blue-400 bg-blue-50'
            : 'border-gray-300 bg-gray-50'
        }`}
      >
        <span aria-hidden="true" className="text-2xl text-gray-400">
          ⬆
        </span>
        <p className="text-sm text-gray-600">
          Drag &amp; drop CSV / TSV / JSON / Excel files here
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT}
          onChange={onInputChange}
          className="sr-only"
          aria-label="Choose data files to upload"
        />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-1 rounded-md border border-gray-300 bg-white px-4 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
        >
          Choose files
        </button>
      </div>

      {/* Optional shared context note */}
      <div className="mt-3">
        <label htmlFor={contextId} className="mb-1 block text-xs font-medium text-gray-600">
          Context note (optional) — describe these files for the agent
        </label>
        <textarea
          id={contextId}
          rows={2}
          value={context}
          onChange={e => setContext(e.target.value)}
          placeholder="e.g. Monthly sales export; the amount column is in USD."
          className="w-full resize-none rounded-md border border-gray-200 p-2 text-sm text-gray-800 placeholder:text-gray-400 focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400"
        />
      </div>

      {/* Upload status rows */}
      {rows.length > 0 && (
        <ul role="list" className="mt-3 space-y-2" aria-label="Upload status">
          {rows.map(row => (
            <li
              key={row.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-gray-200 px-3 py-2 text-xs"
            >
              <span className="min-w-0 flex-1 truncate font-medium text-gray-700">
                {row.name}
              </span>

              {row.state === 'uploading' && (
                <span className="inline-flex items-center gap-1.5 text-blue-600">
                  <Spinner /> Uploading…
                </span>
              )}

              {row.state === 'done' && (
                <span className="text-green-700">✓ {row.message}</span>
              )}

              {row.state === 'error' && (
                <span className="text-red-600" role="alert">
                  ✗ {row.message}
                </span>
              )}

              {row.state === 'duplicate' && (
                <span className="flex flex-wrap items-center gap-2">
                  <span className="text-amber-700">Duplicate</span>
                  <button
                    type="button"
                    onClick={() => dismissRow(row.id)}
                    className="rounded border border-gray-300 bg-white px-2 py-0.5 font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Use existing
                  </button>
                  <button
                    type="button"
                    onClick={() => forceUpload(row.id)}
                    className="rounded border border-amber-300 bg-amber-50 px-2 py-0.5 font-medium text-amber-800 hover:bg-amber-100"
                  >
                    Upload anyway
                  </button>
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent"
    />
  )
}
