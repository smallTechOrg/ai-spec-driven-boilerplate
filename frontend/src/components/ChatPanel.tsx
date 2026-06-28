'use client'

import { useEffect, useRef, useState } from 'react'
import { runAnalysis, AnalysisResult } from '@/lib/api'
import { AnswerCard } from './AnswerCard'

interface ChatMessage {
  id: string
  question: string
  result: AnalysisResult | null
  isLoading: boolean
  error?: string
}

interface ChatPanelProps {
  selectedFileId: string | null
  fileName: string | null
}

export function ChatPanel({ selectedFileId, fileName }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [question, setQuestion] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!question.trim() || !selectedFileId || submitting) return

    const q = question.trim()
    setQuestion('')
    setSubmitting(true)

    const msgId = crypto.randomUUID()

    // Add loading message
    setMessages((prev) => [
      ...prev,
      { id: msgId, question: q, result: null, isLoading: true },
    ])

    try {
      const result = await runAnalysis(selectedFileId, q)
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId
            ? { ...m, isLoading: false, result }
            : m
        )
      )
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Analysis failed.'
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId
            ? { ...m, isLoading: false, error: errorMsg }
            : m
        )
      )
    } finally {
      setSubmitting(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e as unknown as React.FormEvent)
    }
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4 bg-white">
        <h2 className="text-sm font-medium text-gray-700">
          {fileName ? (
            <>
              Analyzing: <span className="text-blue-600">{fileName}</span>
            </>
          ) : (
            <span className="text-gray-400">No file selected</span>
          )}
        </h2>
      </div>

      {/* Message history */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {!selectedFileId && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-400">
            <div className="text-5xl mb-4">📊</div>
            <p className="text-lg font-medium text-gray-500">Upload a CSV file to get started</p>
            <p className="text-sm mt-1">Select a file from the sidebar to begin asking questions</p>
          </div>
        )}

        {selectedFileId && messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-400">
            <p className="text-base font-medium text-gray-500">Ask a question about your data</p>
            <p className="text-sm mt-1">e.g. "What is the total revenue by region?"</p>
          </div>
        )}

        {messages.map((msg) => (
          <AnswerCard
            key={msg.id}
            question={msg.question}
            answer={msg.result?.answer ?? null}
            chartSpec={msg.result?.chart_spec ?? null}
            isLoading={msg.isLoading}
            error={msg.error}
          />
        ))}
      </div>

      {/* Input bar */}
      <div className="border-t border-gray-200 bg-white p-4 shadow-[0_-2px_8px_rgba(0,0,0,0.06)]">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!selectedFileId || submitting}
            placeholder={
              selectedFileId
                ? 'Ask a question about your data...'
                : 'Select a CSV file to ask a question...'
            }
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm shadow-sm
              focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500
              disabled:bg-gray-50 disabled:text-gray-400"
          />
          <button
            type="submit"
            disabled={!selectedFileId || !question.trim() || submitting}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white
              hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? (
              <span className="flex items-center gap-1">
                <span className="h-3 w-3 animate-spin rounded-full border border-white border-t-transparent" />
                <span>Running</span>
              </span>
            ) : (
              'Ask'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
