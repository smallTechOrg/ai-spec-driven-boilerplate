'use client'

import { useState } from 'react'
import { ApiError, AskResponse, Dataset, ask } from '@/lib/api'
import { UploadArea } from '@/components/UploadArea'
import { ProfileCard } from '@/components/ProfileCard'
import { AskBox } from '@/components/AskBox'
import { ConversationThread, Turn } from '@/components/ConversationThread'
import { StubPanel } from '@/components/StubPanel'

export default function Workbench() {
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [turns, setTurns] = useState<Turn[]>([])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastAnswer, setLastAnswer] = useState<AskResponse | null>(null)

  function handleUploaded(ds: Dataset) {
    setDataset(ds)
    // A new dataset starts a fresh conversation/session.
    setConversationId(null)
    setTurns([])
    setError(null)
    setLastAnswer(null)
  }

  async function handleAsk() {
    if (!dataset) return
    const q = question.trim()
    if (!q) return
    setLoading(true)
    setError(null)
    setTurns(prev => [...prev, { role: 'user', content: q }])
    setQuestion('')
    try {
      const res = await ask(dataset.id, q, conversationId)
      setConversationId(res.conversation_id)
      setLastAnswer(res)
      setTurns(prev => [...prev, { role: 'assistant', answer: res }])
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : 'Something went wrong.'
      setError(msg)
      // Keep the question so the user can retry.
      setQuestion(q)
    } finally {
      setLoading(false)
    }
  }

  const hasTurns = turns.length > 0 || loading

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-6 py-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
            ◆
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-800">Data Workbench</h1>
            <p className="text-[11px] text-slate-400">
              Private analysis — your raw rows never leave this machine.
            </p>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-6 py-6 lg:grid-cols-[16rem_minmax(0,1fr)_18rem]">
        {/* Left sidebar — Library (STUB) */}
        <aside className="space-y-4">
          <StubPanel
            title="Dataset Library"
            phase="P2"
            description="Coming soon — your uploaded datasets will live here, ready to switch between."
          />
          <StubPanel
            title="Run History"
            phase="P2"
            description="Coming soon — browse every past question with its code and result, per dataset."
          />
          <StubPanel
            title="Column Notes"
            phase="P4"
            description="Coming soon — annotate columns and business rules the agent will respect."
          />
        </aside>

        {/* Main column */}
        <main className="space-y-6">
          <UploadArea onUploaded={handleUploaded} hasDataset={!!dataset} />

          {!dataset ? (
            <EmptyMain />
          ) : (
            <>
              <ProfileCard dataset={dataset} />

              <section
                aria-label="Conversation"
                className="rounded-xl border border-slate-200 bg-slate-50/60 p-4"
              >
                {hasTurns ? (
                  <ConversationThread
                    turns={turns}
                    loading={loading}
                    error={error}
                    onSuggestion={q => setQuestion(q)}
                  />
                ) : (
                  <div className="py-10 text-center">
                    <p className="text-sm font-medium text-slate-500">
                      Ask a question about your data.
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      The agent will plan, write pandas, run it on the full file, and explain the
                      answer.
                    </p>
                  </div>
                )}

                <div className="mt-4 border-t border-slate-200 pt-4">
                  <AskBox
                    value={question}
                    onChange={setQuestion}
                    onSubmit={handleAsk}
                    disabled={!dataset}
                    loading={loading}
                  />
                </div>
              </section>
            </>
          )}
        </main>

        {/* Right rail — transparency: plan/code summary (real, lives in answers) + cost (STUB) */}
        <aside className="space-y-4">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <h3 className="text-sm font-semibold text-slate-700">Transparency</h3>
            <p className="mt-2 text-xs leading-relaxed text-slate-500">
              Every answer shows the agent&apos;s <strong>plan</strong> and the exact{' '}
              <strong>pandas code</strong> it ran — expand them under each reply. Code runs locally
              on your full file; the model only ever sees schema, stats, and a tiny sample.
            </p>
            {lastAnswer && (
              <dl className="mt-3 space-y-1 border-t border-slate-100 pt-3 text-xs">
                <div className="flex justify-between">
                  <dt className="text-slate-400">Last run status</dt>
                  <dd className="font-medium text-emerald-600">{lastAnswer.status}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-400">Iterations</dt>
                  <dd className="font-medium text-slate-600">{lastAnswer.iterations}</dd>
                </div>
              </dl>
            )}
          </div>

          <StubPanel
            title="Cost Tracker"
            phase="P2"
            description="Coming soon — tokens and estimated $ per query, plus a running daily total."
          />
          <StubPanel
            title="Live Step Trail"
            phase="P3"
            description="Coming soon — watch each plan/execute/refine step stream live with an elapsed timer."
          />
          <StubPanel
            title="Interactive Charts"
            phase="P3"
            description="Coming soon — auto-selected bar/line/scatter charts you can zoom, hover, and filter."
          />
          <StubPanel
            title="Multi-file & Excel"
            phase="P4"
            description="Coming soon — join multiple files and pick sheets from multi-tab Excel workbooks."
          />
        </aside>
      </div>
    </div>
  )
}

function EmptyMain() {
  return (
    <section className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
      <p className="text-base font-medium text-slate-600">Upload a CSV to begin</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-slate-400">
        Drop a spreadsheet above. We&apos;ll profile it in a few seconds — columns, types, ranges,
        and missing values — then you can start asking questions in plain English.
      </p>
    </section>
  )
}
