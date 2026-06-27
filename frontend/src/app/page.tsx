'use client'

import { useState } from 'react'
import { AnomaliesStub, ChartsStub, DatabaseStub } from './StubCards'

type SchemaColumn = {
  name: string
  dtype: string
  friendly_dtype: string
}

type Dataset = {
  dataset_id: string
  filename: string
  row_count: number
  schema: SchemaColumn[]
}

type AskResult = {
  status: string
  answer: string
  error: string | null
}

/** Pull a human-readable message out of the skeleton error envelope. */
function errorMessage(payload: unknown, status: number): string {
  const data = payload as
    | { detail?: { message?: string }; error?: { message?: string } | string }
    | undefined
  return (
    data?.detail?.message ??
    (typeof data?.error === 'object' ? data?.error?.message : data?.error) ??
    `Request failed (${status})`
  )
}

export default function Home() {
  // Upload state
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [dataset, setDataset] = useState<Dataset | null>(null)

  // Ask state
  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)
  const [answer, setAnswer] = useState<AskResult | null>(null)
  const [askError, setAskError] = useState<string | null>(null)

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return
    setUploading(true)
    setUploadError(null)
    setDataset(null)
    setAnswer(null)
    setAskError(null)
    try {
      const body = new FormData()
      body.append('file', file)
      const res = await fetch('/datasets', { method: 'POST', body })
      const payload = await res.json()
      if (!res.ok) {
        setUploadError(errorMessage(payload, res.status))
      } else {
        setDataset(payload.data as Dataset)
      }
    } catch {
      setUploadError('Network error — is the server running?')
    } finally {
      setUploading(false)
    }
  }

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault()
    if (!dataset || !question.trim()) return
    setAsking(true)
    setAskError(null)
    setAnswer(null)
    try {
      const res = await fetch(`/datasets/${dataset.dataset_id}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim() }),
      })
      const payload = await res.json()
      if (!res.ok) {
        setAskError(errorMessage(payload, res.status))
      } else {
        setAnswer(payload.data as AskResult)
      }
    } catch {
      setAskError('Network error — is the server running?')
    } finally {
      setAsking(false)
    }
  }

  const askFailed = answer != null && (answer.status === 'failed' || answer.error != null)

  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <header className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">CSV Analyst</h1>
        <p className="mt-1 text-sm text-gray-600">
          Upload a CSV and ask questions about it in plain English.
        </p>
        <p className="mt-3 flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800">
          <span aria-hidden="true">🔒</span>
          <span>
            Your data stays on your machine — only a summary and your question are sent to
            the AI.
          </span>
        </p>
      </header>

      {/* Upload panel */}
      <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold">1. Upload a CSV</h2>
        <form onSubmit={handleUpload} className="mt-3 flex flex-wrap items-center gap-3">
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={e => {
              setFile(e.target.files?.[0] ?? null)
              setUploadError(null)
            }}
            disabled={uploading}
            className="block text-sm text-gray-700 file:mr-3 file:rounded-md file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100"
          />
          <button
            type="submit"
            disabled={uploading || !file}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {uploading && <Spinner />}
            {uploading ? 'Uploading…' : 'Upload'}
          </button>
        </form>

        {uploadError && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {uploadError}
          </div>
        )}

        {dataset && (
          <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
            <p className="text-sm">
              <span className="font-medium">{dataset.filename}</span>{' '}
              <span className="text-gray-500">
                — {dataset.row_count.toLocaleString()} rows, {dataset.schema.length} columns
              </span>
            </p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {dataset.schema.map(col => (
                <li
                  key={col.name}
                  className="rounded-md border border-gray-200 bg-white px-2.5 py-1 text-xs"
                >
                  <span className="font-medium text-gray-800">{col.name}</span>
                  <span className="ml-1.5 text-gray-400">{col.friendly_dtype}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* Ask panel */}
      <section className="mt-5 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold">2. Ask a question</h2>
        {!dataset && (
          <p className="mt-1 text-sm text-gray-400">Upload a CSV first to ask questions.</p>
        )}
        <form onSubmit={handleAsk} className="mt-3 flex flex-wrap items-center gap-3">
          <input
            type="text"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            placeholder="Ask a question about your data…"
            disabled={!dataset || asking}
            className="min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
          />
          <button
            type="submit"
            disabled={!dataset || asking || !question.trim()}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {asking && <Spinner />}
            {asking ? 'Thinking…' : 'Ask'}
          </button>
        </form>

        {/* Answer panel */}
        <div className="mt-4">
          {asking && (
            <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-500">
              <Spinner />
              Computing locally and asking the AI…
            </div>
          )}

          {!asking && askError && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {askError}
            </div>
          )}

          {!asking && !askError && answer && askFailed && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {answer.error || answer.answer || 'Sorry, that question could not be answered.'}
            </div>
          )}

          {!asking && !askError && answer && !askFailed && (
            <div className="whitespace-pre-wrap rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-900 shadow-sm">
              {answer.answer}
            </div>
          )}

          {!asking && !askError && !answer && (
            <p className="rounded-lg border border-dashed border-gray-200 p-6 text-center text-sm text-gray-400">
              Results will appear here.
            </p>
          )}
        </div>
      </section>

      {/* Labelled, non-functional stubs */}
      <section className="mt-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">
          Also coming
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <ChartsStub />
          <AnomaliesStub />
          <div className="sm:col-span-2">
            <DatabaseStub />
          </div>
        </div>
      </section>
    </main>
  )
}

function Spinner() {
  return (
    <svg
      className="h-4 w-4 animate-spin text-current"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
      />
    </svg>
  )
}
