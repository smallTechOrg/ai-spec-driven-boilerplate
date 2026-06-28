'use client'

import { AskResponse } from '@/lib/api'
import { AnswerPanel } from './AnswerPanel'

export interface UserTurn {
  role: 'user'
  content: string
}
export interface AssistantTurn {
  role: 'assistant'
  answer: AskResponse
}
export type Turn = UserTurn | AssistantTurn

// The session conversation: alternating user questions and assistant answers, oldest first.
export function ConversationThread({
  turns,
  loading,
  error,
  onSuggestion,
}: {
  turns: Turn[]
  loading: boolean
  error: string | null
  onSuggestion: (q: string) => void
}) {
  return (
    <div className="space-y-4">
      {turns.map((turn, i) =>
        turn.role === 'user' ? (
          <div key={i} className="flex justify-end">
            <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2.5 text-sm text-white shadow-sm">
              {turn.content}
            </div>
          </div>
        ) : (
          <div key={i} className="flex justify-start">
            <div className="w-full max-w-[95%] rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3 shadow-sm">
              <AnswerPanel answer={turn.answer} onSuggestion={onSuggestion} />
            </div>
          </div>
        ),
      )}

      {loading && (
        <div className="flex justify-start">
          <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm">
            <svg
              className="h-4 w-4 animate-spin text-indigo-500 motion-reduce:animate-none"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            <span>Working… planning and running pandas on your data.</span>
          </div>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          <span className="font-medium">That run failed.</span> {error} Your question is still in
          the box — try again.
        </div>
      )}
    </div>
  )
}
