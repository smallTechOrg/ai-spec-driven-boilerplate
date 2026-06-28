'use client'

import { useState } from 'react'
import {
  ask as askApi,
  errorMessage,
  uploadDataset,
  type AskResult,
  type Dataset,
} from '../lib/api'
import { TopBar } from '../components/TopBar'
import { LibrarySidebar } from '../components/LibrarySidebar'
import { UploadArea } from '../components/UploadArea'
import { ProfileCard } from '../components/ProfileCard'
import { QuestionBox } from '../components/QuestionBox'
import { RichAnswer } from '../components/RichAnswer'
import { Card, ErrorBanner, Spinner } from '../components/ui'

export default function Home() {
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const [answer, setAnswer] = useState<AskResult | null>(null)
  const [asking, setAsking] = useState(false)
  const [askError, setAskError] = useState<string | null>(null)

  async function handleUpload(file: File) {
    setUploading(true)
    setUploadError(null)
    setAnswer(null)
    setAskError(null)
    try {
      const result = await uploadDataset(file)
      const first = result.datasets[0] ?? null
      setDataset(first)
      if (!first) {
        setUploadError('No dataset was produced from that file.')
      }
    } catch (err) {
      setUploadError(errorMessage(err))
    } finally {
      setUploading(false)
    }
  }

  async function handleAsk(question: string) {
    if (!dataset) return
    setAsking(true)
    setAskError(null)
    setAnswer(null)
    try {
      const result = await askApi(dataset.id, question)
      // A failed run (status:"failed") is a valid envelope, not an error — it
      // is rendered transparently by RichAnswer (shows what was tried).
      setAnswer(result)
    } catch (err) {
      // Only transport / network failures land here.
      setAskError(errorMessage(err))
    } finally {
      setAsking(false)
    }
  }

  const lastCostUsd = answer && answer.status !== 'failed' ? answer.cost.est_usd : null

  return (
    <div className="min-h-screen">
      <TopBar lastCostUsd={lastCostUsd} />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
          {/* Left rail: active dataset (real) + labelled stubs */}
          <LibrarySidebar current={dataset} />

          {/* Workspace column */}
          <div className="space-y-6">
            {/* 1. Upload */}
            <Card>
              <h2 className="mb-3 text-sm font-semibold text-slate-900">1 · Load a file</h2>
              <UploadArea onFile={handleUpload} uploading={uploading} hasDataset={!!dataset} />
              {uploadError && (
                <div className="mt-3">
                  <ErrorBanner title="Couldn't load that file" message={uploadError} />
                </div>
              )}
            </Card>

            {/* 2. Profile (after upload) */}
            {dataset && <ProfileCard dataset={dataset} />}

            {/* 3. Ask */}
            <Card>
              <h2 className="mb-3 text-sm font-semibold text-slate-900">2 · Ask a question</h2>
              <QuestionBox
                onAsk={handleAsk}
                asking={asking}
                disabled={!dataset}
                datasetName={dataset?.name}
              />
              {!dataset && (
                <p className="mt-3 text-xs text-slate-400">
                  Load a CSV or Excel file above to start asking questions.
                </p>
              )}
            </Card>

            {/* 4. Answer area: empty / loading / error / ideal */}
            <section aria-live="polite">
              {asking && (
                <Card>
                  <Spinner label="Planning your query, running it locally, and narrating the result…" />
                  <p className="mt-2 text-xs text-slate-400">
                    Raw rows stay on this machine — only schema &amp; aggregates reach the model.
                  </p>
                </Card>
              )}

              {!asking && askError && (
                <ErrorBanner title="Couldn't get an answer" message={askError} />
              )}

              {!asking && !askError && answer && dataset && (
                <RichAnswer result={answer} dataset={dataset} />
              )}

              {!asking && !askError && !answer && (
                <Card className="border-dashed bg-slate-50/40 text-center">
                  {dataset ? (
                    <p className="py-6 text-sm text-slate-500">
                      Ask a question above to see a rich answer — a plain-language summary, key
                      stats, an auto-picked chart, a table, and a written insight.
                    </p>
                  ) : (
                    <p className="py-6 text-sm text-slate-500">
                      Drop a CSV or Excel file to begin (try{' '}
                      <code className="rounded bg-slate-100 px-1 py-0.5 text-xs text-slate-700">
                        samples/sample_sales.csv
                      </code>
                      ). Your answers will appear here.
                    </p>
                  )}
                </Card>
              )}
            </section>
          </div>
        </div>
      </main>
    </div>
  )
}
