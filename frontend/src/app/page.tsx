'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  askQuery,
  listAudit,
  listDatasets,
  listQueries,
  uploadDataset,
  type AuditEntry,
  type Dataset,
  type Query,
} from '../lib/api'
import { TopNav } from '../components/TopNav'
import { DatasetPanel } from '../components/DatasetPanel'
import { AnswerView } from '../components/AnswerView'
import { AuditPanel } from '../components/AuditPanel'

function errMsg(e: unknown): string {
  if (e instanceof Error) return e.message
  return 'Something went wrong. Please try again.'
}

export default function Home() {
  // Dataset state
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [restoring, setRestoring] = useState(true)

  // Query state
  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)
  const [askError, setAskError] = useState<string | null>(null)
  const [history, setHistory] = useState<Query[]>([])
  const [activeQuery, setActiveQuery] = useState<Query | null>(null)

  // Audit state
  const [audit, setAudit] = useState<AuditEntry[]>([])
  const [auditLoading, setAuditLoading] = useState(true)
  const [auditError, setAuditError] = useState<string | null>(null)

  const refreshAudit = useCallback(async () => {
    setAuditLoading(true)
    setAuditError(null)
    try {
      setAudit(await listAudit())
    } catch (e) {
      setAuditError(errMsg(e))
    } finally {
      setAuditLoading(false)
    }
  }, [])

  const loadHistory = useCallback(async (datasetId: string) => {
    try {
      const queries = await listQueries(datasetId)
      setHistory(queries)
      setActiveQuery(prev => prev ?? queries[0] ?? null)
    } catch {
      // history is non-blocking; audit panel still surfaces failures
    }
  }, [])

  // Session restore on load
  const didInit = useRef(false)
  useEffect(() => {
    if (didInit.current) return
    didInit.current = true
    ;(async () => {
      try {
        const datasets = await listDatasets()
        const active = datasets[0] ?? null
        setDataset(active)
        if (active) await loadHistory(active.id)
      } catch (e) {
        setUploadError(errMsg(e))
      } finally {
        setRestoring(false)
      }
      await refreshAudit()
    })()
  }, [loadHistory, refreshAudit])

  async function handleUpload(file: File) {
    setUploading(true)
    setUploadError(null)
    try {
      const ds = await uploadDataset(file)
      setDataset(ds)
      setHistory([])
      setActiveQuery(null)
      setAskError(null)
      await loadHistory(ds.id)
    } catch (e) {
      setUploadError(errMsg(e))
    } finally {
      setUploading(false)
      await refreshAudit()
    }
  }

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault()
    if (!dataset || !question.trim() || asking) return
    setAsking(true)
    setAskError(null)
    try {
      const q = await askQuery(dataset.id, question.trim())
      setActiveQuery(q)
      setHistory(prev => [q, ...prev])
      setQuestion('')
    } catch (e) {
      setAskError(errMsg(e))
    } finally {
      setAsking(false)
      await refreshAudit()
    }
  }

  const askDisabled = !dataset || asking || restoring

  return (
    <div className="min-h-screen">
      <TopNav />

      <main className="mx-auto max-w-7xl px-6 py-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
          {/* Main column */}
          <div className="flex flex-col gap-6">
            <DatasetPanel
              dataset={dataset}
              uploading={uploading}
              error={uploadError}
              onUpload={handleUpload}
            />

            {/* Ask box */}
            <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 text-sm font-semibold text-gray-900">Ask a question</h2>
              <form onSubmit={handleAsk} className="flex flex-col gap-2 sm:flex-row">
                <input
                  type="text"
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                  disabled={askDisabled}
                  placeholder={
                    dataset
                      ? 'e.g. What is the total revenue by region?'
                      : 'Upload a dataset first to ask questions'
                  }
                  aria-label="Question"
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-2.5 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
                />
                <button
                  type="submit"
                  disabled={askDisabled || !question.trim()}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {asking && (
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                  )}
                  {asking ? 'Analyzing…' : 'Ask'}
                </button>
              </form>
              {!dataset && !restoring && (
                <p className="mt-2 text-xs text-gray-400">
                  The ask box turns on once a dataset is loaded.
                </p>
              )}
              {askError && (
                <p className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  {askError}
                </p>
              )}
            </section>

            {/* Answer */}
            {asking && (
              <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <div className="flex items-center gap-3 text-sm text-gray-500">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
                  Generating SQL, running it locally, and writing the answer…
                </div>
              </section>
            )}

            {!asking && activeQuery && <AnswerView query={activeQuery} />}

            {!asking && !activeQuery && dataset && (
              <section className="rounded-xl border border-dashed border-gray-300 bg-white p-8 text-center">
                <p className="text-sm text-gray-500">
                  Ask your first question above to see a formatted answer and a data table here.
                </p>
              </section>
            )}

            {/* Query history */}
            {dataset && history.length > 0 && (
              <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <h2 className="mb-3 text-sm font-semibold text-gray-900">
                  History <span className="text-gray-400">({history.length})</span>
                </h2>
                <ul className="flex max-h-72 flex-col gap-1.5 overflow-y-auto pr-1">
                  {history.map(q => {
                    const selected = activeQuery?.id === q.id
                    return (
                      <li key={q.id}>
                        <button
                          type="button"
                          onClick={() => setActiveQuery(q)}
                          className={`flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition ${
                            selected
                              ? 'border-blue-300 bg-blue-50 text-blue-800'
                              : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'
                          }`}
                        >
                          <span
                            className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                              q.status === 'failed' ? 'bg-red-500' : 'bg-green-500'
                            }`}
                          />
                          <span className="truncate">{q.question}</span>
                        </button>
                      </li>
                    )
                  })}
                </ul>
              </section>
            )}
          </div>

          {/* Side panel */}
          <div className="lg:sticky lg:top-6 lg:max-h-[calc(100vh-3rem)]">
            <AuditPanel entries={audit} loading={auditLoading} error={auditError} />
          </div>
        </div>
      </main>
    </div>
  )
}
