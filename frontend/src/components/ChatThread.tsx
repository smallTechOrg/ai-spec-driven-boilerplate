'use client'

import { useState, useRef, useEffect } from 'react'
import type { SSEEvent, QueryResult, ChartSpec } from '../lib/api'
import { streamChat } from '../lib/api'
import RichResponse from './RichResponse'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  status?: string
  // For assistant messages being built from SSE stream
  narrative?: string
  queryResult?: QueryResult
  chartSpec?: ChartSpec
  sql?: string
  isStreaming?: boolean
  statusMessage?: string
  error?: string
}

interface InitialMessage {
  message_id: string
  role: 'user' | 'assistant'
  content: string
  status: string
}

interface Props {
  sessionId: string
  datasets: number // number of datasets — used to gate the Ask button
  initialMessages?: InitialMessage[]
}

function parseAssistantContent(content: string): Partial<ChatMessage> {
  try {
    const r = JSON.parse(content)
    return {
      narrative: r.narrative,
      queryResult: r.query_result,
      chartSpec: r.chart_spec,
      sql: r.sql,
    }
  } catch {
    // Content is plain text (e.g. older messages or errors)
    return { narrative: content }
  }
}

function mapInitialMessage(m: InitialMessage): ChatMessage {
  if (m.role === 'assistant') {
    const parsed = parseAssistantContent(m.content)
    return {
      id: m.message_id,
      role: 'assistant',
      content: m.content,
      status: m.status,
      ...parsed,
    }
  }
  return { id: m.message_id, role: 'user', content: m.content, status: m.status }
}

export default function ChatThread({ sessionId, datasets, initialMessages = [] }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    initialMessages.map(mapInitialMessage)
  )
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const stopRef = useRef<(() => void) | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Reset messages when sessionId changes
  useEffect(() => {
    setMessages(initialMessages.map(mapInitialMessage))
    setStreaming(false)
    setInput('')
    if (stopRef.current) {
      stopRef.current()
      stopRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  // Update messages when initialMessages prop changes (e.g., after session load)
  useEffect(() => {
    setMessages(initialMessages.map(mapInitialMessage))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialMessages])

  // Auto-resize textarea
  function handleInputChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 96)}px` // max ~3 lines
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!streaming && input.trim() && datasets > 0) {
        submitQuestion(input.trim())
      }
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!input.trim() || streaming || datasets === 0) return
    submitQuestion(input.trim())
  }

  function submitQuestion(question: string) {
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    setStreaming(true)

    // Append user message immediately
    const userMsgId = `user-${Date.now()}`
    setMessages((prev) => [...prev, { id: userMsgId, role: 'user', content: question }])

    // Append placeholder assistant message
    const asstMsgId = `asst-${Date.now()}`
    setMessages((prev) => [
      ...prev,
      {
        id: asstMsgId,
        role: 'assistant',
        content: '',
        isStreaming: true,
        statusMessage: 'Analysing question...',
      },
    ])

    let narrative = ''
    let queryResult: QueryResult | undefined
    let chartSpec: ChartSpec | undefined
    let sql: string | undefined

    const stop = streamChat(sessionId, question, (evt: SSEEvent) => {
      if (evt.type === 'status') {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === asstMsgId ? { ...m, statusMessage: evt.data.message } : m
          )
        )
      } else if (evt.type === 'chunk') {
        narrative += evt.data.text
        setMessages((prev) =>
          prev.map((m) =>
            m.id === asstMsgId ? { ...m, narrative, statusMessage: undefined } : m
          )
        )
      } else if (evt.type === 'table') {
        queryResult = evt.data
        setMessages((prev) =>
          prev.map((m) => (m.id === asstMsgId ? { ...m, queryResult } : m))
        )
      } else if (evt.type === 'chart') {
        chartSpec = evt.data
        setMessages((prev) =>
          prev.map((m) => (m.id === asstMsgId ? { ...m, chartSpec } : m))
        )
      } else if (evt.type === 'error') {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === asstMsgId
              ? { ...m, error: evt.data.message, isStreaming: false, statusMessage: undefined }
              : m
          )
        )
        setStreaming(false)
      } else if (evt.type === 'done') {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === asstMsgId
              ? { ...m, isStreaming: false, statusMessage: undefined, sql }
              : m
          )
        )
        setStreaming(false)
      }
    })

    stopRef.current = stop
  }

  const canAsk = !streaming && input.trim().length > 0 && datasets > 0

  return (
    <div className="flex flex-col h-full">
      {/* Message thread */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <p className="text-lg mb-2">Upload a dataset and ask a question to get started.</p>
            <p className="text-sm text-gray-400">
              Example: &quot;What are the top 5 rows by revenue?&quot;
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'user' ? (
              <div className="max-w-lg rounded-2xl bg-blue-600 px-4 py-2 text-sm text-white">
                {msg.content}
              </div>
            ) : (
              <div className="max-w-2xl w-full rounded-2xl bg-white border border-gray-200 px-4 py-3 shadow-sm">
                {msg.statusMessage && (
                  <p className="text-xs text-blue-500 mb-2 flex items-center gap-1">
                    <span className="inline-block w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                    <em>{msg.statusMessage}</em>
                  </p>
                )}
                {msg.error ? (
                  <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3">
                    Could not answer this question: {msg.error}
                  </div>
                ) : (
                  <RichResponse
                    response={{
                      narrative: msg.narrative,
                      query_result: msg.queryResult,
                      chart_spec: msg.chartSpec,
                      sql: msg.sql,
                    }}
                    isStreaming={msg.isStreaming}
                  />
                )}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="border-t border-gray-200 p-4">
        <form onSubmit={handleSubmit} className="flex gap-2 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              disabled={streaming}
              placeholder={
                datasets === 0
                  ? 'Upload at least one dataset first...'
                  : streaming
                    ? 'Analysing...'
                    : 'Ask a question about your data...'
              }
              rows={1}
              className="w-full rounded-xl border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50 resize-none overflow-hidden"
              style={{ minHeight: '38px' }}
              title={datasets === 0 ? 'Upload at least one dataset first.' : undefined}
            />
          </div>
          <button
            type="submit"
            disabled={!canAsk}
            title={datasets === 0 ? 'Upload at least one dataset first.' : undefined}
            className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 shrink-0"
          >
            {streaming ? 'Analysing...' : 'Ask'}
          </button>
        </form>
        <p className="mt-1 text-xs text-gray-400 text-center">
          Powered by Gemini 2.5 Flash + DuckDB · Shift+Enter for newline
        </p>
      </div>
    </div>
  )
}
