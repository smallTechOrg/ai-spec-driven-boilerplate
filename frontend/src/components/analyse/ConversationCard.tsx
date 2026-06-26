'use client'

import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { api, type AskResponse } from '@/lib/api'
import type { LastQueryTokens } from '@/components/analyse/AnalyseTab'
import { Markdown } from '@/components/analyse/Markdown'
import { StepsInspector } from '@/components/analyse/StepsInspector'

/**
 * Conversation card (C2, C6, C7, C22, C23) — REAL in Phase 2.
 *
 * A question textarea (Enter submits, Shift+Enter inserts a newline) plus an
 * Ask button (spinner + disabled while a question runs). On Ask → POST /ask
 * with the selected `dataset_id`. The answer is rendered Markdown
 * (`answer_markdown` via react-markdown), with iteration + token counts, a
 * "Best effort" badge when `is_best_effort`, and a collapsible Steps inspector.
 *
 * Turns accumulate in a thread (role="log", aria-live="polite") so the latest
 * Q&A is announced. While a question runs, /runs/current is polled ~1/s to show
 * a lightweight progress row — best-effort, never blocking the request.
 *
 * Ask is disabled until a dataset is selected, with a hint to upload/select one.
 * Follow-up suggestion chips are not rendered in Phase 2 (the API returns an
 * empty list); a short "coming later" hint is shown in their place.
 */

interface Turn {
  id: string
  question: string
  // Pending while the request is in flight; then resolved to answer or error.
  pending: boolean
  answer?: AskResponse
  error?: string
}

let turnSeq = 0
function nextTurnId(): string {
  turnSeq += 1
  return `t${turnSeq}-${Date.now()}`
}

export function ConversationCard({
  selectedDatasetId,
  onAnswered,
}: {
  selectedDatasetId: string | null
  onAnswered: (tokens: LastQueryTokens) => void
}) {
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState<{ iteration: number; max: number } | null>(null)
  const questionId = useId()
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const canAsk = !!selectedDatasetId && question.trim().length > 0 && !running

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    setProgress(null)
  }, [])

  // Clean up any poll on unmount.
  useEffect(() => stopPolling, [stopPolling])

  const updateTurn = useCallback((id: string, patch: Partial<Turn>) => {
    setTurns(prev => prev.map(t => (t.id === id ? { ...t, ...patch } : t)))
  }, [])

  const submit = useCallback(async () => {
    const datasetId = selectedDatasetId
    const q = question.trim()
    if (!datasetId || !q || running) return

    const turnId = nextTurnId()
    setTurns(prev => [...prev, { id: turnId, question: q, pending: true }])
    setQuestion('')
    setRunning(true)

    // Best-effort live progress poll (~1/s). Never blocks the ask.
    pollRef.current = setInterval(() => {
      api
        .currentRun()
        .then(run => {
          if (run && run.status === 'running') {
            setProgress({ iteration: run.iteration_count, max: run.max_iterations })
          }
        })
        .catch(() => {
          /* polling is best-effort — ignore transient errors */
        })
    }, 1000)

    try {
      const res = await api.ask(datasetId, q)
      updateTurn(turnId, { pending: false, answer: res })
      onAnswered({ input: res.tokens_input, output: res.tokens_output })
    } catch (err) {
      updateTurn(turnId, {
        pending: false,
        error: err instanceof Error ? err.message : 'The question failed to run.',
      })
    } finally {
      stopPolling()
      setRunning(false)
    }
  }, [selectedDatasetId, question, running, updateTurn, onAnswered, stopPolling])

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Enter submits; Shift+Enter inserts a newline.
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        if (canAsk) void submit()
      }
    },
    [canAsk, submit],
  )

  return (
    <section
      aria-labelledby="conversation-heading"
      className="flex min-h-[24rem] flex-col rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 id="conversation-heading" className="text-sm font-semibold text-gray-800">
          Conversation
        </h2>
      </div>

      {/* Thread */}
      <div
        role="log"
        aria-live="polite"
        aria-label="Conversation thread"
        className="flex flex-1 flex-col gap-3 overflow-y-auto rounded-md border border-gray-100 bg-gray-50/50 p-3"
      >
        {turns.length === 0 ? (
          <div className="flex flex-1 items-center justify-center text-center">
            <p className="text-xs text-gray-400">
              {selectedDatasetId
                ? 'Ask a question about the selected dataset to get started.'
                : 'Upload a CSV and select it above, then ask a question here.'}
            </p>
          </div>
        ) : (
          turns.map(turn => <TurnView key={turn.id} turn={turn} />)
        )}
      </div>

      {/* Live progress row (only while running) */}
      {running && (
        <div className="mt-2" aria-live="polite">
          <div className="mb-1 flex items-center justify-between text-[11px] text-gray-500">
            <span className="inline-flex items-center gap-1.5">
              <Spinner /> Thinking…
            </span>
            {progress && (
              <span className="tabular-nums">
                Step {progress.iteration} / {progress.max}
              </span>
            )}
          </div>
          <div
            role="progressbar"
            aria-label="Agent progress"
            aria-valuemin={0}
            aria-valuemax={progress?.max ?? 0}
            aria-valuenow={progress?.iteration ?? 0}
            className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100"
          >
            <div
              className="h-full bg-blue-500 transition-all"
              style={{
                width: progress && progress.max > 0
                  ? `${Math.min(100, (progress.iteration / progress.max) * 100)}%`
                  : '15%',
              }}
            />
          </div>
        </div>
      )}

      {/* Composer */}
      <div className="mt-3">
        <label htmlFor={questionId} className="sr-only">
          Ask a question about your data
        </label>
        <textarea
          id={questionId}
          rows={3}
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={running}
          placeholder={
            selectedDatasetId
              ? 'Ask a question about your data…'
              : 'Select a dataset above to ask a question…'
          }
          className="w-full resize-none rounded-md border border-gray-200 p-3 text-sm text-gray-800 placeholder:text-gray-400 focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400 disabled:bg-gray-50 disabled:text-gray-400"
        />
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
          <span className="text-xs text-gray-400">
            {selectedDatasetId
              ? 'Enter to send · Shift+Enter for a new line'
              : 'No dataset selected — pick one in Tables above.'}
          </span>
          <button
            type="button"
            onClick={() => void submit()}
            disabled={!canAsk}
            title={
              !selectedDatasetId
                ? 'Select a dataset first'
                : question.trim().length === 0
                  ? 'Type a question first'
                  : undefined
            }
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300 disabled:text-gray-500"
          >
            {running && <Spinner />}
            {running ? 'Asking…' : 'Ask'}
          </button>
        </div>

        {/* Follow-up suggestions are a Phase-3 feature (API returns []). */}
        <p className="mt-2 text-[11px] text-gray-400">
          Follow-up suggestions and saved sessions arrive in a later phase.
        </p>
      </div>
    </section>
  )
}

/** A single conversation turn: the question, then the pending/answer/error body. */
function TurnView({ turn }: { turn: Turn }) {
  return (
    <div className="space-y-2">
      {/* Question (blue) */}
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-lg rounded-br-sm bg-blue-600 px-3 py-2 text-sm text-white">
          {turn.question}
        </div>
      </div>

      {/* Answer / pending / error */}
      <div className="rounded-lg rounded-bl-sm border border-gray-200 bg-white px-3 py-2">
        {turn.pending ? (
          <p className="inline-flex items-center gap-2 text-xs text-gray-500">
            <Spinner /> The agent is working on it…
          </p>
        ) : turn.error ? (
          <p role="alert" className="text-sm text-red-600">
            {turn.error}
          </p>
        ) : turn.answer ? (
          <AnswerView answer={turn.answer} />
        ) : null}
      </div>
    </div>
  )
}

function AnswerView({ answer }: { answer: AskResponse }) {
  return (
    <div>
      {/* Best-effort badge */}
      {answer.is_best_effort && (
        <div className="mb-2">
          <span className="rounded bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">
            Best effort
          </span>
        </div>
      )}

      <Markdown>{answer.answer_markdown ?? ''}</Markdown>

      {/* Meta: iterations + token counts */}
      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-gray-100 pt-2 text-[11px] text-gray-500">
        <span className="tabular-nums">
          {answer.iteration_count} iteration{answer.iteration_count === 1 ? '' : 's'}
        </span>
        <span aria-hidden="true">·</span>
        <span className="tabular-nums">
          Tokens: {answer.tokens_input} in / {answer.tokens_output} out
        </span>
        {answer.status && (
          <>
            <span aria-hidden="true">·</span>
            <span>status: {answer.status}</span>
          </>
        )}
      </div>

      <StepsInspector steps={answer.steps ?? []} />
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
