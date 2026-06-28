'use client'

import { useState } from 'react'
import {
  askDataset,
  ApiError,
  type AnalysisRun,
  type DatasetBundle,
} from '@/lib/api'
import Library from '@/components/Library'
import ProfilePanel from '@/components/ProfilePanel'
import AskBox from '@/components/AskBox'
import AnswerCard from '@/components/AnswerCard'
import InspectorStubs from '@/components/InspectorStubs'

export default function Home() {
  const [bundle, setBundle] = useState<DatasetBundle | null>(null)
  const [run, setRun] = useState<AnalysisRun | null>(null)
  const [asking, setAsking] = useState(false)
  const [askError, setAskError] = useState<string | null>(null)
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null)

  function handleUploaded(b: DatasetBundle) {
    setBundle(b)
    setRun(null)
    setAskError(null)
    setPendingQuestion(null)
  }

  async function handleAsk(question: string) {
    if (!bundle) return
    setAsking(true)
    setAskError(null)
    setRun(null)
    setPendingQuestion(question)
    try {
      const { run: result } = await askDataset(bundle.dataset.id, question)
      setRun(result)
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? e.message
          : 'Could not reach the server. Is it running on this machine?'
      setAskError(msg)
    } finally {
      setAsking(false)
      setPendingQuestion(null)
    }
  }

  const hasDataset = !!bundle

  return (
    <div className="flex h-screen flex-col bg-slate-50 text-slate-900">
      <header className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-5 py-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
            DC
          </span>
          <div>
            <h1 className="text-sm font-semibold leading-tight text-slate-800">DataChat</h1>
            <p className="text-[11px] leading-tight text-slate-400">
              Ask your spreadsheets in plain language — your rows never leave this machine.
            </p>
          </div>
        </div>
        <span className="hidden rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-700 sm:inline">
          Local · private
        </span>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[260px_minmax(0,1fr)_320px]">
        {/* LIBRARY (left rail) */}
        <aside className="hidden overflow-y-auto border-r border-slate-200 bg-white p-4 lg:block">
          <Library active={bundle?.dataset ?? null} onUploaded={handleUploaded} />
        </aside>

        {/* CONVERSATION (center) */}
        <main className="flex min-h-0 flex-col">
          <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
            <div className="mx-auto max-w-2xl space-y-4">
              {!hasDataset && <EmptyState />}

              {hasDataset && !run && !asking && !askError && (
                <IdleWithDataset name={bundle!.dataset.name} />
              )}

              {asking && <Analyzing question={pendingQuestion} />}

              {askError && !asking && (
                <div
                  role="alert"
                  className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700"
                >
                  <p className="font-medium">That request didn&apos;t go through.</p>
                  <p className="mt-1 text-rose-600">{askError}</p>
                </div>
              )}

              {run && !asking && <AnswerCard run={run} />}
            </div>
          </div>

          {/* On mobile, the upload control lives inline above the ask box. */}
          {!hasDataset && (
            <div className="border-t border-slate-200 bg-white p-4 lg:hidden">
              <Library active={null} onUploaded={handleUploaded} />
            </div>
          )}

          <div className="shrink-0 border-t border-slate-200 bg-white px-4 py-3 sm:px-8">
            <div className="mx-auto max-w-2xl">
              <AskBox disabled={!hasDataset} busy={asking} onAsk={handleAsk} />
            </div>
          </div>
        </main>

        {/* INSPECTOR (right) */}
        <aside className="hidden overflow-y-auto border-l border-slate-200 bg-slate-50 p-4 xl:block">
          {bundle ? (
            <div className="space-y-4">
              <ProfilePanel bundle={bundle} />
              <InspectorStubs />
            </div>
          ) : (
            <div className="space-y-4">
              <div className="rounded-xl border border-dashed border-slate-300 bg-white p-4 text-center text-sm text-slate-400">
                <p className="font-medium text-slate-500">No dataset profiled yet</p>
                <p className="mt-1 text-xs">
                  Upload a file and its columns, dtypes, ranges and row count appear here.
                </p>
              </div>
              <InspectorStubs />
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
        <svg
          className="h-6 w-6"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
      </div>
      <h2 className="text-base font-semibold text-slate-800">Upload a dataset to begin</h2>
      <p className="mx-auto mt-1.5 max-w-md text-sm text-slate-500">
        Drop a CSV or Excel file in the panel on the left. DataChat profiles it locally, then you can
        ask questions in plain language. The agent writes pandas code that runs on your machine — the
        raw rows are never sent to the model.
      </p>
      <ul className="mx-auto mt-4 max-w-xs space-y-1.5 text-left text-xs text-slate-500">
        <li className="flex items-center gap-2">
          <Dot /> Auto-profiles columns, dtypes and ranges
        </li>
        <li className="flex items-center gap-2">
          <Dot /> Shows the exact code behind every number
        </li>
        <li className="flex items-center gap-2">
          <Dot /> Reports the tokens + cost per question
        </li>
      </ul>
    </div>
  )
}

function IdleWithDataset({ name }: { name: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
      <h2 className="text-base font-semibold text-slate-800">Ready to analyze</h2>
      <p className="mt-1.5 text-sm text-slate-500">
        <span className="font-medium text-slate-700">{name}</span> is loaded and profiled. Ask a
        question below to get a coded answer.
      </p>
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        {[
          'What is the total revenue by region?',
          'How many rows have missing values?',
          'What is the average order value?',
        ].map(q => (
          <span
            key={q}
            className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-500"
          >
            {q}
          </span>
        ))}
      </div>
      <p className="mt-3 text-[11px] text-slate-400">Examples — type your own question below.</p>
    </div>
  )
}

function Analyzing({ question }: { question: string | null }) {
  return (
    <div className="space-y-3">
      {question && (
        <div className="flex justify-end">
          <p className="max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-sm text-white shadow-sm">
            {question}
          </p>
        </div>
      )}
      <div className="flex items-center gap-3 rounded-2xl rounded-tl-sm border border-slate-200 bg-white p-4 shadow-sm">
        <span
          className="h-5 w-5 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600 motion-reduce:animate-none"
          aria-hidden="true"
        />
        <div>
          <p className="text-sm font-medium text-slate-700">Analyzing…</p>
          <p className="text-xs text-slate-400">
            Planning, writing pandas, and running it locally over your data.
          </p>
        </div>
      </div>
    </div>
  )
}

function Dot() {
  return <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" aria-hidden="true" />
}
