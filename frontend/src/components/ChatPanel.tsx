'use client'

import { useEffect, useRef, useState } from 'react'
import { Message, MessageBubble } from './MessageBubble'
import { runQuery } from '@/lib/api'

interface ChatPanelProps {
  sessionId: string
  activeDatasetId: string | null
  hasDatasets: boolean
}

export function ChatPanel({ sessionId, activeDatasetId, hasDatasets }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      text: 'Hello! Upload a CSV file on the left, then ask me anything about your data.',
      tableData: null,
    },
  ])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const q = question.trim()
    if (!q || !activeDatasetId || loading) return

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      text: q,
      tableData: null,
    }
    const thinkingMsg: Message = {
      id: `thinking-${Date.now()}`,
      role: 'assistant',
      text: null,
      tableData: null,
      thinking: true,
    }
    setMessages((prev) => [...prev, userMsg, thinkingMsg])
    setQuestion('')
    setLoading(true)

    try {
      const result = await runQuery(sessionId, activeDatasetId, q)
      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        text: result.answer_text,
        tableData: result.table_data,
      }
      setMessages((prev) => prev.filter((m) => !m.thinking).concat(assistantMsg))
    } catch (err: unknown) {
      const errMsg: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        text: null,
        tableData: null,
        error:
          err instanceof Error
            ? err.message
            : 'Network error — is the server running?',
      }
      setMessages((prev) => prev.filter((m) => !m.thinking).concat(errMsg))
    } finally {
      setLoading(false)
    }
  }

  const canSend = !!activeDatasetId && !!question.trim() && !loading

  return (
    <div className="flex flex-col h-full">
      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 p-4">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={!hasDatasets || loading}
            placeholder={
              !hasDatasets
                ? 'Upload a CSV to start asking questions'
                : activeDatasetId
                  ? 'Ask a question about your data…'
                  : 'Select a file on the left to start'
            }
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
          />
          <button
            type="submit"
            disabled={!canSend}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
          >
            {loading ? (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
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
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            ) : (
              'Send'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
