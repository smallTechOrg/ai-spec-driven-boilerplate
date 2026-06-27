'use client'

import { useState } from 'react'

type SchemaCol = { name: string; dtype: string }

type Dataset = {
  dataset_id: string
  filename: string
  row_count: number
  schema: SchemaCol[]
  sample_preview: Record<string, unknown>[]
}

type AskResult = {
  query_id?: string
  dataset_id?: string
  status: 'completed' | 'failed'
  answer?: string
  explanation?: string
  code?: string | null
  result?: unknown
  error?: string
  model?: string
  latency_ms?: number
}

// The static export is mounted at /app; the API lives at the server root.
// Always call absolute-from-origin paths so they resolve at the root, NOT under /app.
const API_DATASETS = '/datasets'
const askUrl = (id: string) => `/datasets/${id}/ask`

export default function Home() {
  // upload state
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [dataset, setDataset] = useState<Dataset | null>(null)

  // ask state
  const [question, setQuestion] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [askError, setAskError] = useState<string | null>(null)
  const [answer, setAnswer] = useState<AskResult | null>(null)

  const [copied, setCopied] = useState(false)

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadError(null)
    setDataset(null)
    setAnswer(null)
    setAskError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(API_DATASETS, { method: 'POST', body: form })
      const body = await res.json().catch(() => null)
      if (!res.ok) {
        const msg =
          body?.detail?.message ??
          body?.error?.message ??
          "Couldn't read that file as a CSV."
        setUploadError(msg)
      } else {
        setDataset(body.data as Dataset)
      }
    } catch {
      setUploadError('Network error — is the server running?')
    } finally {
      setUploading(false)
      // allow re-selecting the same file
      e.target.value = ''
    }
  }

  async function handleAnalyze(e: React.FormEvent) {
    e.preventDefault()
    if (!dataset || !question.trim()) return
    setAnalyzing(true)
    setAskError(null)
    setAnswer(null)
    try {
      const res = await fetch(askUrl(dataset.dataset_id), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim(), conversation_id: '' }),
      })
      const body = await res.json().catch(() => null)
      if (!res.ok) {
        const msg =
          body?.detail?.message ??
          body?.error?.message ??
          `Request failed (${res.status})`
        setAskError(msg)
      } else {
        setAnswer(body.data as AskResult)
      }
    } catch {
      setAskError('Network error — is the server running?')
    } finally {
      setAnalyzing(false)
    }
  }

  async function copyCode() {
    if (!answer?.code) return
    try {
      await navigator.clipboard.writeText(answer.code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard unavailable — ignore */
    }
  }

  const failed = answer?.status === 'failed'

  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      {/* Header */}
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Data Analysis Agent</h1>
        <p className="mt-2 text-sm text-gray-600">
          Upload a CSV, ask a question, see the answer and the exact code it ran. Your
          data stays on your machine.
        </p>
      </header>

      {/* Upload control */}
      <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-gray-900">1. Upload a dataset</h2>
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-400">
            .xlsx (coming soon)
          </span>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-3">
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            {uploading ? 'Uploading…' : dataset ? 'Choose a different CSV' : 'Choose a CSV file'}
            <input
              type="file"
              accept=".csv,text/csv"
              className="sr-only"
              onChange={handleUpload}
              disabled={uploading}
            />
          </label>

          {/* STUB: multi-file */}
          <button
            type="button"
            disabled
            title="Coming soon"
            className="inline-flex cursor-not-allowed items-center gap-2 rounded-lg border border-dashed border-gray-300 px-4 py-2 text-sm font-medium text-gray-400"
          >
            + Add another file
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs">Coming soon</span>
          </button>
        </div>

        {uploadError && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {uploadError}
          </div>
        )}

        {dataset && (
          <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-3">
            <p className="text-sm text-green-800">
              <span className="font-semibold">{dataset.filename}</span> — {dataset.row_count}{' '}
              rows
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {dataset.schema.map(col => (
                <span
                  key={col.name}
                  className="rounded-full bg-white px-2 py-0.5 text-xs text-gray-700 ring-1 ring-gray-200"
                >
                  {col.name}
                  <span className="ml-1 text-gray-400">{col.dtype}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Question box */}
      <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-900">2. Ask a question</h2>
        <form onSubmit={handleAnalyze} className="mt-3 space-y-3">
          <textarea
            className="w-full rounded-lg border border-gray-300 p-3 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
            rows={3}
            placeholder={
              dataset
                ? 'e.g. What is the total amount, and which region has the highest average amount?'
                : 'Upload a CSV to get started'
            }
            value={question}
            onChange={e => setQuestion(e.target.value)}
            disabled={!dataset || analyzing}
          />
          <button
            type="submit"
            disabled={!dataset || analyzing || !question.trim()}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {analyzing && (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            )}
            {analyzing ? 'Analyzing…' : 'Analyze'}
          </button>
        </form>
      </section>

      {/* Answer panel / states */}
      <section className="mt-6">
        {askError && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {askError}
          </div>
        )}

        {answer && failed && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            {answer.error ?? 'Could not compute an answer for this question.'}
          </div>
        )}

        {answer && !failed && (
          <div className="space-y-4 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
                Answer
              </p>
              <p className="mt-1 text-xl font-semibold text-gray-900">{answer.answer}</p>
            </div>

            {answer.explanation && (
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
                  Explanation
                </p>
                <p className="mt-1 text-sm leading-relaxed text-gray-700">
                  {answer.explanation}
                </p>
              </div>
            )}

            {answer.code && (
              <div>
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
                    The exact code that produced this answer
                  </p>
                  <button
                    type="button"
                    onClick={copyCode}
                    className="rounded-md border border-gray-200 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50"
                  >
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <pre className="mt-1 overflow-x-auto rounded-lg bg-gray-900 p-4 text-xs leading-relaxed text-gray-100">
                  <code className="font-mono">{answer.code}</code>
                </pre>
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {!answer && !askError && !analyzing && (
          <p className="rounded-xl border border-dashed border-gray-200 bg-white/50 p-8 text-center text-sm text-gray-400">
            {dataset
              ? 'Ask a question above to see the answer, explanation, and code.'
              : 'Upload a CSV to get started.'}
          </p>
        )}
      </section>

      {/* STUB: Continue the conversation (Phase 2) */}
      <section className="mt-6 rounded-xl border border-dashed border-gray-300 bg-gray-50 p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-400">Continue the conversation</h2>
          <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-500">
            Coming soon
          </span>
        </div>
        <div className="mt-3 flex gap-2">
          <input
            type="text"
            disabled
            placeholder="Ask a follow-up question…"
            className="w-full cursor-not-allowed rounded-lg border border-gray-200 bg-white/60 p-2.5 text-sm text-gray-400"
          />
          <button
            type="button"
            disabled
            className="cursor-not-allowed rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-400"
          >
            Send
          </button>
        </div>
      </section>

      {/* STUB: Charts (Phase 4) */}
      <section className="mt-6 rounded-xl border border-dashed border-gray-300 bg-gray-50 p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-400">Charts</h2>
          <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-500">
            Coming soon
          </span>
        </div>
        <div className="mt-3 flex h-32 items-center justify-center rounded-lg border border-gray-200 bg-white/60 text-sm text-gray-400">
          Charts (coming soon)
        </div>
      </section>

      {/* STUB: Connect a database */}
      <section className="mt-6 mb-12">
        <button
          type="button"
          disabled
          title="Coming soon"
          className="inline-flex cursor-not-allowed items-center gap-2 rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-2.5 text-sm font-medium text-gray-400"
        >
          Connect a database
          <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs">Coming soon</span>
        </button>
      </section>
    </main>
  )
}
