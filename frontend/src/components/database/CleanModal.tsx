'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError, type CleanPreviewResponse } from '@/lib/api'

/**
 * NL data-cleaning modal (C24) — preview + apply.
 *
 * Flow:
 *  1. The user types a plain-English instruction ("drop rows with nulls").
 *  2. **Preview** → POST /datasets/{id}/clean runs the generated pandas on a COPY
 *     and returns the code + before/after row+col counts (never mutates).
 *  3. **Apply** → POST /datasets/{id}/clean/apply runs the previewed code in
 *     place, rewriting the files and updating counts; on success the parent
 *     refreshes via `onApplied`.
 *
 * A clean exec error (422) surfaces inline; the dataset is never changed on a
 * failed preview. Backdrop + Escape close; focus the instruction field on open.
 */
export function CleanModal({
  datasetId,
  filename,
  open,
  onClose,
  onApplied,
}: {
  datasetId: string | null
  filename: string | null
  open: boolean
  onClose: () => void
  onApplied: (id: string) => void
}) {
  const [instruction, setInstruction] = useState('')
  const [previewing, setPreviewing] = useState(false)
  const [applying, setApplying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<CleanPreviewResponse | null>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Reset state each time the modal opens for a (possibly new) dataset.
  useEffect(() => {
    if (open) {
      setInstruction('')
      setPreview(null)
      setError(null)
      setPreviewing(false)
      setApplying(false)
    }
  }, [open, datasetId])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const runPreview = useCallback(async () => {
    if (!datasetId) return
    const text = instruction.trim()
    if (!text) return
    setPreviewing(true)
    setError(null)
    setPreview(null)
    try {
      const res = await api.cleanPreview(datasetId, text)
      setPreview(res)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError(err instanceof Error ? err.message : 'Failed to preview the cleaning.')
      }
    } finally {
      setPreviewing(false)
    }
  }, [datasetId, instruction])

  const runApply = useCallback(async () => {
    if (!datasetId || !preview) return
    setApplying(true)
    setError(null)
    try {
      await api.cleanApply(datasetId, { code: preview.code, instruction: instruction.trim() })
      onApplied(datasetId)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply the cleaning.')
    } finally {
      setApplying(false)
    }
  }, [datasetId, preview, instruction, onApplied, onClose])

  if (!open || !datasetId) return null

  const busy = previewing || applying

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onMouseDown={e => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="clean-modal-title"
        className="flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-lg bg-white shadow-xl"
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
          <h2 id="clean-modal-title" className="text-sm font-semibold text-gray-800">
            Clean dataset{filename ? ` — ${filename}` : ''}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close clean dialog"
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          <p className="mb-2 text-xs text-gray-500">
            Describe the cleaning in plain English. We&apos;ll generate the pandas,
            preview its effect on a copy, and only change the dataset when you apply.
          </p>

          <label htmlFor="clean-instruction" className="sr-only">
            Cleaning instruction
          </label>
          <textarea
            id="clean-instruction"
            ref={inputRef}
            rows={2}
            value={instruction}
            onChange={e => setInstruction(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                if (!busy && instruction.trim()) void runPreview()
              }
            }}
            placeholder="e.g. drop rows with nulls; trim whitespace from the name column"
            className="w-full resize-none rounded-md border border-gray-200 p-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400 disabled:bg-gray-50"
            disabled={busy}
          />

          <div className="mt-2 flex justify-end">
            <button
              type="button"
              onClick={() => void runPreview()}
              disabled={busy || instruction.trim().length === 0}
              className="inline-flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {previewing && <Spinner />}
              {previewing ? 'Previewing…' : 'Preview'}
            </button>
          </div>

          {error && (
            <p role="alert" className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              {error}
            </p>
          )}

          {preview && (
            <div className="mt-4 space-y-3">
              <div className="flex flex-wrap items-center gap-3 rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-700">
                <span className="tabular-nums">
                  Rows: <strong>{preview.before_row_count}</strong> →{' '}
                  <strong>{preview.after_row_count}</strong>
                </span>
                <span aria-hidden="true" className="text-gray-300">
                  ·
                </span>
                <span className="tabular-nums">
                  Cols: <strong>{preview.before_col_count}</strong> →{' '}
                  <strong>{preview.after_col_count}</strong>
                </span>
              </div>

              <div>
                <p className="mb-1 text-[11px] font-medium text-gray-500">Generated code</p>
                <pre className="overflow-x-auto rounded-md bg-gray-900 px-3 py-2 font-mono text-[11px] leading-relaxed text-gray-100">
                  <code>{preview.code}</code>
                </pre>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-gray-200 px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void runApply()}
            disabled={!preview || busy}
            title={!preview ? 'Preview first' : undefined}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300 disabled:text-gray-500"
          >
            {applying && <Spinner />}
            {applying ? 'Applying…' : 'Apply'}
          </button>
        </div>
      </div>
    </div>
  )
}

function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
    />
  )
}
