'use client'

import { useMemo, useRef, useState } from 'react'
import {
  askQuestion,
  uploadDataset,
  type AnswerData,
  type DatasetProfile,
  type StepName,
  type StepStatus,
} from '@/lib/api'
import { AnswerCard, type Turn } from '@/components/AnswerCard'
import { Header } from '@/components/Header'
import { LibrarySidebar } from '@/components/LibrarySidebar'
import { ProfilePanel } from '@/components/ProfilePanel'
import { StubActions } from '@/components/StubActions'
import { INITIAL_STEPS, type StepMap } from '@/components/StepStatus'
import { Spinner } from '@/components/UploadZone'
import { UploadZone } from '@/components/UploadZone'

function uid(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36)
}

export default function Home() {
  const [dataset, setDataset] = useState<DatasetProfile | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const [turns, setTurns] = useState<Turn[]>([])
  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)
  const conversationId = useRef<string | null>(null)
  const threadEnd = useRef<HTMLDivElement>(null)

  const { sessionCost, sessionTokens } = useMemo(() => {
    let cost = 0
    let tokens = 0
    for (const t of turns) {
      if (t.answer) {
        cost += t.answer.estimated_cost_usd ?? 0
        tokens += t.answer.token_usage?.total ?? 0
      }
    }
    return { sessionCost: cost, sessionTokens: tokens }
  }, [turns])

  async function handleUpload(file: File) {
    setUploading(true)
    setUploadError(null)
    try {
      const profile = await uploadDataset(file)
      setDataset(profile)
      setTurns([])
      conversationId.current = null
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : 'Something went wrong.')
    } finally {
      setUploading(false)
    }
  }

  function patchTurn(id: string, patch: Partial<Turn>) {
    setTurns(prev => prev.map(t => (t.id === id ? { ...t, ...patch } : t)))
  }

  function patchStep(id: string, step: StepName, status: StepStatus) {
    setTurns(prev =>
      prev.map(t => {
        if (t.id !== id) return t
        const steps: StepMap = { ...t.steps, [step]: status }
        // mark earlier steps done once a later one begins
        return { ...t, steps }
      }),
    )
  }

  async function ask(q: string) {
    if (!dataset || !q.trim() || asking) return
    const id = uid()
    const turn: Turn = {
      id,
      question: q.trim(),
      status: 'running',
      steps: { ...INITIAL_STEPS },
      answer: null,
      error: null,
    }
    setTurns(prev => [...prev, turn])
    setQuestion('')
    setAsking(true)
    setTimeout(() => threadEnd.current?.scrollIntoView({ behavior: 'smooth' }), 50)

    try {
      const data: AnswerData = await askQuestion(
        dataset.dataset_id,
        q.trim(),
        conversationId.current,
        (step, status) => patchStep(id, step, status),
      )
      if (data.conversation_id) conversationId.current = data.conversation_id
      patchTurn(id, {
        status: 'done',
        answer: data,
        steps: { plan: 'done', generate_code: 'done', execute_local: 'done', visualize: 'done' },
      })
    } catch (e) {
      patchTurn(id, {
        status: 'error',
        error: e instanceof Error ? e.message : 'Something went wrong.',
      })
    } finally {
      setAsking(false)
      setTimeout(() => threadEnd.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Header sessionCost={sessionCost} sessionTokens={sessionTokens} />

      <main className="mx-auto flex max-w-6xl gap-6 px-6 py-6">
        <LibrarySidebar />

        <div className="min-w-0 flex-1 space-y-6">
          {/* Upload / profile */}
          {!dataset ? (
            <section className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-800">Start by uploading a CSV</h2>
                <p className="text-sm text-slate-500">
                  We profile every column locally, then you can ask questions in plain English.
                  The model only ever sees the schema and a tiny sample — your raw rows stay on this machine.
                </p>
              </div>
              <UploadZone onUpload={handleUpload} loading={uploading} error={uploadError} />
              <StubActions />
            </section>
          ) : (
            <section className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-semibold text-slate-800">Dataset profile</h2>
                <button
                  type="button"
                  onClick={() => {
                    setDataset(null)
                    setTurns([])
                    setUploadError(null)
                    conversationId.current = null
                  }}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                >
                  Upload a different file
                </button>
              </div>
              <ProfilePanel dataset={dataset} />
              <StubActions />
            </section>
          )}

          {/* Chat thread */}
          {dataset && (
            <section className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-800">Ask a question</h2>

              {turns.length === 0 && !asking && (
                <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center">
                  <p className="text-sm font-medium text-slate-600">No questions yet.</p>
                  <p className="mt-1 text-sm text-slate-400">
                    Try something like &ldquo;how many rows per {dataset.profile[0]?.name ?? 'category'}?&rdquo;
                  </p>
                </div>
              )}

              <div className="space-y-4">
                {turns.map(turn => (
                  <AnswerCard key={turn.id} turn={turn} onFollowUp={ask} asking={asking} />
                ))}
              </div>
              <div ref={threadEnd} />

              <form
                onSubmit={e => {
                  e.preventDefault()
                  ask(question)
                }}
                className="sticky bottom-4 flex items-end gap-2 rounded-xl border border-slate-200 bg-white p-2 shadow-sm"
              >
                <textarea
                  className="max-h-32 min-h-[44px] flex-1 resize-none rounded-lg border-0 px-3 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  rows={1}
                  placeholder={`Ask about ${dataset.name}…`}
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      ask(question)
                    }
                  }}
                  disabled={asking}
                  aria-label="Ask a question about your dataset"
                />
                <button
                  type="submit"
                  disabled={asking || !question.trim()}
                  className="flex h-[44px] items-center gap-2 rounded-lg bg-indigo-600 px-5 text-sm font-medium text-white transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-50"
                >
                  {asking ? (
                    <>
                      <Spinner className="h-4 w-4 text-white" />
                      Thinking…
                    </>
                  ) : (
                    'Ask'
                  )}
                </button>
              </form>
            </section>
          )}
        </div>
      </main>
    </div>
  )
}
