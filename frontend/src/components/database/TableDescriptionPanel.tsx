'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  api,
  ApiError,
  type DatasetDetail,
  type PreviewResponse,
} from '@/lib/api'
import { _erKeysFor, type ErDataset, type ErKeys } from '@/components/database/ERDiagramPanel'
import { CleanModal } from '@/components/database/CleanModal'

/**
 * Table Description panel — REAL (Phase 4).
 *
 * Shows everything about the selected dataset (spec/ui.md "Table Description
 * panel"):
 *  - filename + origin/stale badges + "rows × cols · FORMAT";
 *  - a derived block (parent chips + collapsible derivation code) when derived;
 *  - a Keys block whose PK/FK come from `_erKeysFor` — the SAME inference the ER
 *    diagram uses (imported, never re-implemented), so badges and edges agree;
 *  - a columns table (Name | Type with PK/FK badges) from `columns_schema`;
 *  - a Context-notes textarea that AUTO-SAVES (debounced) via PATCH
 *    /datasets/{id}/context, plus a "Generate notes" button that POSTs /describe
 *    then polls GET /datasets/{id} on `auto_notes_status` until done/failed;
 *  - a ~10-row data preview via GET /datasets/{id}/preview;
 *  - actions: Clean (modal), Re-derive (derived+stale only), Delete (confirm).
 */
export function TableDescriptionPanel({
  datasetId,
  allDatasets,
  onChanged,
  onDeleted,
}: {
  datasetId: string | null
  allDatasets: ErDataset[]
  /** Called after a mutation that changes counts/columns (clean / re-derive / notes). */
  onChanged: () => void
  /** Called after a successful delete with the deleted id. */
  onDeleted: (id: string) => void
}) {
  const [detail, setDetail] = useState<DatasetDetail | null>(null)
  const [preview, setPreview] = useState<PreviewResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [showCode, setShowCode] = useState(false)
  const [cleanOpen, setCleanOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [busy, setBusy] = useState<null | 'rederive' | 'delete' | 'describe'>(null)

  // Context-notes editing (debounced auto-save).
  const [notes, setNotes] = useState('')
  const [savingNotes, setSavingNotes] = useState(false)
  const [savedNotes, setSavedNotes] = useState(false)
  const [notesStatus, setNotesStatus] = useState<string | null>(null)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // --- load detail + preview when the selection changes --------------------
  const loadDetail = useCallback(
    async (id: string) => {
      setLoading(true)
      setError(null)
      try {
        const [d, p] = await Promise.all([
          api.getDataset(id),
          api.preview(id, 10).catch(() => null),
        ])
        setDetail(d)
        setPreview(p)
        setNotes(d.context ?? '')
        setNotesStatus(d.auto_notes_status ?? null)
        setShowCode(false)
        setConfirmDelete(false)
        setSavedNotes(false)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dataset details.')
        setDetail(null)
        setPreview(null)
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  useEffect(() => {
    // Clear any in-flight timers when the selection changes / unmounts.
    if (saveTimer.current) clearTimeout(saveTimer.current)
    if (pollTimer.current) clearTimeout(pollTimer.current)
    if (!datasetId) {
      setDetail(null)
      setPreview(null)
      setNotes('')
      setNotesStatus(null)
      return
    }
    void loadDetail(datasetId)
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current)
      if (pollTimer.current) clearTimeout(pollTimer.current)
    }
  }, [datasetId, loadDetail])

  // --- keys (PK/FK) from the single-source-of-truth inference --------------
  const keys: ErKeys = useMemo(
    () => (datasetId ? _erKeysFor(datasetId, allDatasets) : { pk: [], fk: [] }),
    [datasetId, allDatasets],
  )
  const pkSet = useMemo(() => new Set(keys.pk), [keys.pk])
  const fkMap = useMemo(
    () => new Map(keys.fk.map(f => [f.column, f.references] as const)),
    [keys.fk],
  )

  // --- context notes: debounced auto-save ----------------------------------
  const onNotesChange = useCallback(
    (value: string) => {
      setNotes(value)
      setSavedNotes(false)
      if (!datasetId) return
      if (saveTimer.current) clearTimeout(saveTimer.current)
      saveTimer.current = setTimeout(() => {
        setSavingNotes(true)
        api
          .patchContext(datasetId, value)
          .then(() => {
            setSavedNotes(true)
            onChanged()
          })
          .catch((err: unknown) => {
            setError(err instanceof Error ? err.message : 'Failed to save notes.')
          })
          .finally(() => setSavingNotes(false))
      }, 800)
    },
    [datasetId, onChanged],
  )

  // --- Generate notes (C30): trigger then poll auto_notes_status -----------
  const pollNotes = useCallback(
    (id: string, attempt = 0) => {
      pollTimer.current = setTimeout(async () => {
        try {
          const d = await api.getDataset(id)
          setNotesStatus(d.auto_notes_status ?? null)
          if (d.auto_notes_status === 'done' || d.auto_notes_status === 'failed') {
            if (d.auto_notes_status === 'done') {
              setNotes(d.context ?? '')
              setDetail(prev => (prev ? { ...prev, context: d.context } : d))
              onChanged()
            }
            setBusy(null)
            return
          }
        } catch {
          // transient — keep polling within the budget
        }
        if (attempt < 40) pollNotes(id, attempt + 1)
        else setBusy(null) // give up after ~80s; status stays "pending"
      }, 2000)
    },
    [onChanged],
  )

  const generateNotes = useCallback(async () => {
    if (!datasetId) return
    setBusy('describe')
    setError(null)
    setNotesStatus('pending')
    try {
      await api.describeDataset(datasetId)
      pollNotes(datasetId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start notes generation.')
      setNotesStatus(detail?.auto_notes_status ?? null)
      setBusy(null)
    }
  }, [datasetId, pollNotes, detail])

  // --- Re-derive (C25; derived + stale only) -------------------------------
  const doReDerive = useCallback(async () => {
    if (!datasetId) return
    setBusy('rederive')
    setError(null)
    try {
      await api.reDerive(datasetId)
      await loadDetail(datasetId)
      onChanged()
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Failed to re-derive the dataset.',
      )
    } finally {
      setBusy(null)
    }
  }, [datasetId, loadDetail, onChanged])

  // --- Delete --------------------------------------------------------------
  const doDelete = useCallback(async () => {
    if (!datasetId) return
    setBusy('delete')
    setError(null)
    try {
      await api.deleteDataset(datasetId)
      setConfirmDelete(false)
      onDeleted(datasetId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete the dataset.')
    } finally {
      setBusy(null)
    }
  }, [datasetId, onDeleted])

  // --- render --------------------------------------------------------------
  const derived = detail?.origin === 'derived'
  const stale = detail?.stale === true
  const parentIds = detail?.derived_from_dataset_ids ?? []
  const nameById = useMemo(
    () => new Map(allDatasets.map(d => [d.id, d.filename] as const)),
    [allDatasets],
  )

  return (
    <section
      aria-labelledby="description-heading"
      className="flex flex-col rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 id="description-heading" className="text-sm font-semibold text-gray-800">
          Table description
        </h2>
        {derived && (
          <span className="inline-flex items-center gap-1.5">
            <span className="rounded-full border border-green-200 bg-green-50 px-2 py-0.5 text-[11px] font-medium text-green-700">
              derived
            </span>
            {stale && (
              <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700">
                stale
              </span>
            )}
          </span>
        )}
      </div>

      {!datasetId ? (
        <div className="rounded-md border border-dashed border-gray-200 px-3 py-10 text-center text-xs text-gray-400">
          Select a dataset in the diagram to see its details.
        </div>
      ) : loading && !detail ? (
        <div className="rounded-md border border-dashed border-gray-200 px-3 py-10 text-center text-xs text-gray-400">
          Loading dataset details…
        </div>
      ) : error && !detail ? (
        <div
          role="alert"
          className="flex flex-col items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-6 text-center text-xs text-red-700"
        >
          <span>{error}</span>
          <button
            type="button"
            onClick={() => void loadDetail(datasetId)}
            className="rounded border border-red-300 bg-white px-2 py-0.5 font-medium text-red-700 hover:bg-red-100"
          >
            Retry
          </button>
        </div>
      ) : detail ? (
        <div className="flex flex-col gap-4">
          {/* Inline (non-fatal) error banner */}
          {error && (
            <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              {error}
            </p>
          )}

          {/* Filename + size summary */}
          <div>
            <p className="truncate text-sm font-semibold text-gray-900" title={detail.filename}>
              {detail.filename}
            </p>
            <p className="mt-0.5 text-xs text-gray-500 tabular-nums">
              {detail.row_count.toLocaleString()} rows × {detail.col_count} cols ·{' '}
              {detail.format?.toUpperCase()}
            </p>
          </div>

          {/* Derived lineage block */}
          {derived && (
            <div className="rounded-md border border-green-100 bg-green-50/60 p-3">
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-green-700">
                Derived from
              </p>
              {detail.derivation_description && (
                <p className="mb-2 text-xs text-gray-600">{detail.derivation_description}</p>
              )}
              <div className="flex flex-wrap gap-1.5">
                {parentIds.length === 0 ? (
                  <span className="text-xs text-gray-400">No parent datasets recorded.</span>
                ) : (
                  parentIds.map(pid => (
                    <span
                      key={pid}
                      className="rounded-full border border-gray-200 bg-white px-2 py-0.5 text-[11px] text-gray-700"
                    >
                      {nameById.get(pid) ?? pid}
                    </span>
                  ))
                )}
              </div>
              {detail.derivation_code && (
                <div className="mt-2">
                  <button
                    type="button"
                    onClick={() => setShowCode(v => !v)}
                    aria-expanded={showCode ? 'true' : 'false'}
                    className="text-[11px] font-medium text-green-700 hover:text-green-900"
                  >
                    {showCode ? 'Hide' : 'Show'} derivation code
                  </button>
                  {showCode && (
                    <pre className="mt-1.5 overflow-x-auto rounded-md bg-gray-900 px-3 py-2 font-mono text-[11px] leading-relaxed text-gray-100">
                      <code>{detail.derivation_code}</code>
                    </pre>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Keys block (PK/FK from _erFkLinks) */}
          <div>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-500">
              Keys
            </p>
            {keys.pk.length === 0 && keys.fk.length === 0 ? (
              <p className="text-xs text-gray-400">No inferred keys.</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {keys.pk.map(col => (
                  <span
                    key={`pk-${col}`}
                    className="inline-flex items-center gap-1 rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-800"
                  >
                    <span className="font-bold">PK</span>
                    {col}
                  </span>
                ))}
                {keys.fk.map(f => (
                  <span
                    key={`fk-${f.column}`}
                    className="inline-flex items-center gap-1 rounded border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-800"
                    title={`References ${f.references}`}
                  >
                    <span className="font-bold">FK</span>
                    {f.column} → {f.references}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Columns table */}
          <div>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-500">
              Columns
            </p>
            <div className="overflow-hidden rounded-md border border-gray-200">
              <table className="w-full text-left text-xs">
                <thead className="bg-gray-50 text-[11px] uppercase tracking-wide text-gray-500">
                  <tr>
                    <th className="px-2.5 py-1.5 font-medium">Name</th>
                    <th className="px-2.5 py-1.5 font-medium">Type</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.columns_schema.map((c, i) => {
                    const isPk = pkSet.has(c.name)
                    const fkRef = fkMap.get(c.name)
                    return (
                      <tr key={c.name} className={i % 2 === 1 ? 'bg-gray-50/60' : undefined}>
                        <td className="px-2.5 py-1.5 font-medium text-gray-800">
                          <span className="inline-flex items-center gap-1.5">
                            {c.name}
                            {isPk && (
                              <span className="rounded border border-amber-200 bg-amber-50 px-1 text-[10px] font-bold text-amber-700">
                                PK
                              </span>
                            )}
                            {fkRef && (
                              <span
                                className="rounded border border-blue-200 bg-blue-50 px-1 text-[10px] font-bold text-blue-700"
                                title={`References ${fkRef}`}
                              >
                                FK
                              </span>
                            )}
                          </span>
                        </td>
                        <td className="px-2.5 py-1.5 text-gray-500">{c.dtype}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Context notes (auto-save) + Generate notes (C30) */}
          <div>
            <div className="mb-1.5 flex items-center justify-between gap-2">
              <label
                htmlFor="context-notes"
                className="text-[11px] font-semibold uppercase tracking-wide text-gray-500"
              >
                Context notes
              </label>
              <span className="flex items-center gap-2 text-[11px] text-gray-400">
                {savingNotes ? (
                  <span>Saving…</span>
                ) : savedNotes ? (
                  <span className="text-green-600">Saved</span>
                ) : null}
                <button
                  type="button"
                  onClick={() => void generateNotes()}
                  disabled={busy === 'describe' || notesStatus === 'pending'}
                  className="inline-flex items-center gap-1.5 rounded-md border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {(busy === 'describe' || notesStatus === 'pending') && <Spinner />}
                  {notesStatus === 'pending' ? 'Generating…' : 'Generate notes'}
                </button>
              </span>
            </div>
            <textarea
              id="context-notes"
              rows={3}
              value={notes}
              onChange={e => onNotesChange(e.target.value)}
              placeholder="Add context about this dataset (units, caveats, what columns mean)…"
              className="w-full resize-y rounded-md border border-gray-200 p-2.5 text-xs text-gray-800 placeholder:text-gray-400 focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
            {notesStatus === 'failed' && (
              <p className="mt-1 text-[11px] text-amber-700">
                Notes generation failed. You can edit the notes manually or try again.
              </p>
            )}
          </div>

          {/* Data preview (~10 rows) */}
          <div>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-500">
              Preview
            </p>
            {preview && preview.columns.length > 0 ? (
              <div className="overflow-x-auto rounded-md border border-gray-200">
                <table className="w-full text-left text-[11px]">
                  <thead className="bg-gray-50 uppercase tracking-wide text-gray-500">
                    <tr>
                      {preview.columns.map(col => (
                        <th key={col} className="whitespace-nowrap px-2.5 py-1.5 font-medium">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((row, ri) => (
                      <tr key={ri} className={ri % 2 === 1 ? 'bg-gray-50/60' : undefined}>
                        {preview.columns.map((col, ci) => (
                          <td
                            key={col}
                            className="whitespace-nowrap px-2.5 py-1.5 tabular-nums text-gray-700"
                          >
                            {formatCell(cellValue(row, col, ci))}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="rounded-md border border-dashed border-gray-200 px-3 py-4 text-center text-xs text-gray-400">
                No preview rows available.
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="flex flex-wrap items-center gap-2 border-t border-gray-100 pt-3">
            <button
              type="button"
              onClick={() => setCleanOpen(true)}
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
            >
              Clean
            </button>

            {derived && stale && (
              <button
                type="button"
                onClick={() => void doReDerive()}
                disabled={busy === 'rederive'}
                className="inline-flex items-center gap-1.5 rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {busy === 'rederive' && <Spinner />}
                {busy === 'rederive' ? 'Re-deriving…' : 'Re-derive'}
              </button>
            )}

            <span className="ml-auto">
              {confirmDelete ? (
                <span className="inline-flex items-center gap-2">
                  <span className="text-xs text-gray-600">Delete this dataset?</span>
                  <button
                    type="button"
                    onClick={() => void doDelete()}
                    disabled={busy === 'delete'}
                    className="inline-flex items-center gap-1.5 rounded-md border border-red-300 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {busy === 'delete' && <Spinner />}
                    {busy === 'delete' ? 'Deleting…' : 'Yes'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmDelete(false)}
                    disabled={busy === 'delete'}
                    className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-60"
                  >
                    No
                  </button>
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => setConfirmDelete(true)}
                  className="rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100"
                >
                  Delete
                </button>
              )}
            </span>
          </div>
        </div>
      ) : null}

      {/* NL cleaning modal (C24) */}
      <CleanModal
        datasetId={cleanOpen ? datasetId : null}
        filename={detail?.filename ?? null}
        open={cleanOpen}
        onClose={() => setCleanOpen(false)}
        onApplied={id => {
          setCleanOpen(false)
          void loadDetail(id)
          onChanged()
        }}
      />
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

/** Read a preview cell — the API returns row OBJECTS keyed by column name. */
function cellValue(row: unknown, col: string, index: number): unknown {
  if (Array.isArray(row)) return row[index]
  if (row && typeof row === 'object') return (row as Record<string, unknown>)[col]
  return undefined
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') return value.toLocaleString()
  return String(value)
}
