'use client'

import { useState } from 'react'
import { Analysis, Dataset, runAnalysis, uploadDataset } from '@/lib/api'
import Sidebar from '@/components/Sidebar'
import UploadZone from '@/components/UploadZone'
import ProfilePanel from '@/components/ProfilePanel'
import WorkingIndicator from '@/components/WorkingIndicator'
import AnswerBubble from '@/components/AnswerBubble'

interface Turn {
  id: string
  question: string
  analysis: Analysis
}

export default function Home() {
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [running, setRunning] = useState(false)
  const [askError, setAskError] = useState<string | null>(null)

  async function handleUpload(file: File) {
    setUploading(true)
    setUploadError(null)
    try {
      const ds = await uploadDataset(file)
      setDataset(ds)
      setTurns([])
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault()
    if (!dataset || !question.trim() || running) return
    const q = question.trim()
    setRunning(true)
    setAskError(null)
    setQuestion('')
    try {
      const analysis = await runAnalysis(dataset.id, q)
      setTurns(prev => [...prev, { id: analysis.id, question: q, analysis }])
    } catch (e) {
      setAskError(e instanceof Error ? e.message : 'Analysis failed')
      setQuestion(q)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar datasetName={dataset?.filename ?? null} />

      <main className="flex flex-1 flex-col">
        <header className="border-b border-slate-200 bg-white px-6 py-4">
          <h1 className="text-lg font-bold tracking-tight text-slate-900">
            Data Analysis Agent
          </h1>
          <p className="text-xs text-slate-500">
            Upload a CSV, then ask in plain language. Your rows never leave this machine.
          </p>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          {!dataset ? (
            <div className="flex h-full items-center justify-center">
              <UploadZone onFile={handleUpload} uploading={uploading} error={uploadError} />
            </div>
          ) : (
            <div className="mx-auto flex max-w-3xl flex-col gap-6">
              <ProfilePanel dataset={dataset} />

              {turns.length === 0 && !running && (
                <p
                  data-testid="empty-chat"
                  className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500"
                >
                  Ask your first question below — e.g. &ldquo;What&apos;s the average value by
                  category?&rdquo;
                </p>
              )}

              {turns.map(turn => (
                <div key={turn.id} className="space-y-2">
                  <div className="ml-auto max-w-[80%] rounded-xl rounded-br-sm bg-indigo-600 px-4 py-2 text-sm text-white">
                    {turn.question}
                  </div>
                  <AnswerBubble analysis={turn.analysis} />
                </div>
              ))}

              {running && <WorkingIndicator />}

              {askError && (
                <div
                  role="alert"
                  className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
                >
                  {askError}
                </div>
              )}
            </div>
          )}
        </div>

        {dataset && (
          <form
            onSubmit={handleAsk}
            className="border-t border-slate-200 bg-white px-6 py-4"
          >
            <div className="mx-auto flex max-w-3xl items-end gap-2">
              <textarea
                data-testid="question-input"
                className="min-h-[44px] flex-1 resize-none rounded-lg border border-slate-300 p-2.5 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                rows={1}
                placeholder="Ask a question about this dataset…"
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) handleAsk(e)
                }}
                disabled={running}
              />
              <button
                type="submit"
                data-testid="ask-button"
                disabled={running || !question.trim()}
                className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-50"
              >
                {running ? 'Analyzing…' : 'Ask'}
              </button>
            </div>
          </form>
        )}
      </main>
    </div>
  )
}
