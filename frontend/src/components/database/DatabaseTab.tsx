'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, type DatasetSummary } from '@/lib/api'
import { ERDiagramPanel, type ErDataset } from '@/components/database/ERDiagramPanel'
import { TableDescriptionPanel } from '@/components/database/TableDescriptionPanel'

/**
 * Database tab — REAL (Phase 4).
 *
 * Fetches the data universe (`GET /datasets`) and renders the schema ER diagram
 * (the single-source-of-truth `<ERDiagramPanel>`) beside the per-dataset
 * `<TableDescriptionPanel>`. The diagram and the description panel share one
 * `selectedId` so clicking a table card drives the right-hand detail view.
 *
 * The list is fetched on mount (the tab re-mounts when shown, so this is also
 * the "re-fetch when the tab is shown" hook) and re-fetched after any mutation
 * (clean / re-derive / delete / clear-database) via a bumped refresh token. The
 * header shows the uploaded/derived counts and a REAL danger "Clear database"
 * action behind an inline confirm that calls `DELETE /datasets`.
 */
export function DatabaseTab() {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const [confirmClear, setConfirmClear] = useState(false)
  const [clearing, setClearing] = useState(false)

  // Bumped after a child mutation so the list (and counts) re-fetch.
  const [refreshToken, setRefreshToken] = useState(0)
  const refresh = useCallback(() => setRefreshToken(t => t + 1), [])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await api.listDatasets()
      setDatasets(Array.isArray(list) ? list : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load the database.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load, refreshToken])

  // Keep the selection valid as the universe changes: default to the first
  // dataset, and drop a selection whose dataset was deleted.
  useEffect(() => {
    if (datasets.length === 0) {
      if (selectedId !== null) setSelectedId(null)
      return
    }
    if (selectedId === null || !datasets.some(d => d.id === selectedId)) {
      setSelectedId(datasets[0].id)
    }
  }, [datasets, selectedId])

  const uploadedCount = useMemo(
    () => datasets.filter(d => d.origin !== 'derived').length,
    [datasets],
  )
  const derivedCount = useMemo(
    () => datasets.filter(d => d.origin === 'derived').length,
    [datasets],
  )

  const doClear = useCallback(async () => {
    setClearing(true)
    setError(null)
    try {
      await api.clearAllDatasets()
      setConfirmClear(false)
      setSelectedId(null)
      setDatasets([])
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear the database.')
    } finally {
      setClearing(false)
    }
  }, [refresh])

  // The diagram + badges need column metadata; `GET /datasets` carries `columns`.
  const erDatasets = datasets as ErDataset[]
  const isEmpty = !loading && !error && datasets.length === 0

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div>
          <h2 className="text-sm font-semibold text-gray-800">Database</h2>
          <p className="mt-0.5 text-xs text-gray-500 tabular-nums">
            {loading && datasets.length === 0
              ? 'Loading…'
              : `${datasets.length} dataset${datasets.length === 1 ? '' : 's'} · ${uploadedCount} uploaded · ${derivedCount} derived`}
          </p>
        </div>

        {confirmClear ? (
          <span className="inline-flex items-center gap-2">
            <span className="text-xs text-gray-600">
              Delete ALL datasets and sessions?
            </span>
            <button
              type="button"
              onClick={() => void doClear()}
              disabled={clearing}
              className="inline-flex items-center gap-1.5 rounded-md border border-red-300 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {clearing && <Spinner />}
              {clearing ? 'Clearing…' : 'Yes, clear'}
            </button>
            <button
              type="button"
              onClick={() => setConfirmClear(false)}
              disabled={clearing}
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-60"
            >
              Cancel
            </button>
          </span>
        ) : (
          <button
            type="button"
            onClick={() => setConfirmClear(true)}
            disabled={datasets.length === 0}
            title={
              datasets.length === 0
                ? 'No datasets to clear'
                : 'Delete every dataset, derived set, query, and session'
            }
            className="rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-50 disabled:text-gray-300"
          >
            Clear database
          </button>
        )}
      </div>

      {error && (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700"
        >
          <span>{error}</span>
          <button
            type="button"
            onClick={() => void load()}
            className="rounded border border-red-300 bg-white px-2 py-0.5 font-medium text-red-700 hover:bg-red-100"
          >
            Retry
          </button>
        </div>
      )}

      {isEmpty ? (
        <div className="flex flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-gray-200 bg-white px-4 py-16 text-center">
          <span aria-hidden="true" className="mb-1 text-3xl text-gray-300">
            ⬚
          </span>
          <p className="text-sm font-medium text-gray-500">No datasets yet</p>
          <p className="text-xs text-gray-400">
            Upload a CSV on the Analyse tab — its schema and details appear here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.4fr_1fr]">
          <ERDiagramPanel
            datasets={erDatasets}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
          <TableDescriptionPanel
            datasetId={selectedId}
            allDatasets={erDatasets}
            onChanged={refresh}
            onDeleted={id => {
              setDatasets(prev => prev.filter(d => d.id !== id))
              if (selectedId === id) setSelectedId(null)
              refresh()
            }}
          />
        </div>
      )}
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
