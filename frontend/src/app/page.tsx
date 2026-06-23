'use client'

import { useState, useEffect, useCallback } from 'react'
import SessionSidebar from '../components/SessionSidebar'
import DatasetPanel from '../components/DatasetPanel'
import ChatThread from '../components/ChatThread'
import { createSession, listSessions, getSession } from '../lib/api'
import type { Session, Dataset, Message } from '../lib/api'

const SESSION_KEY = 'analyst_session_id'

// Audit log stub — Phase 1 placeholder
function AuditLogDrawer({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="flex-1 bg-black/30" onClick={onClose} />
      {/* Drawer */}
      <div className="w-96 bg-white h-full shadow-xl flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h2 className="font-semibold text-gray-800">Audit Log</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            aria-label="Close audit log"
          >
            ×
          </button>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
          <p className="text-gray-600 mb-2">
            This panel will show every SQL query the agent ran, with dataset name, row count, and
            latency.
          </p>
          <p className="text-sm text-gray-400 mt-4 border border-dashed border-gray-300 rounded px-4 py-2">
            [Coming in Phase 2]
          </p>
        </div>
      </div>
    </div>
  )
}

export default function Home() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [loadingSession, setLoadingSession] = useState(false)
  const [loadingSessions, setLoadingSessions] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showAuditLog, setShowAuditLog] = useState(false)

  // Load the full session list
  const loadSessions = useCallback(async (): Promise<Session[]> => {
    try {
      const list = await listSessions()
      setSessions(list)
      return list
    } catch {
      return []
    }
  }, [])

  // Load a session's datasets + messages
  const loadSessionData = useCallback(async (sessionId: string) => {
    setLoadingSession(true)
    setError(null)
    try {
      const { session: s, datasets: d, messages: m } = await getSession(sessionId)
      setDatasets(d)
      setMessages(m as Message[])
      setSessions((prev) => {
        const exists = prev.find((x) => x.session_id === sessionId)
        if (!exists) return [...prev, s]
        return prev.map((x) => (x.session_id === sessionId ? { ...x, ...s } : x))
      })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load session')
    } finally {
      setLoadingSession(false)
    }
  }, [])

  // On mount: restore session from localStorage and load session list
  useEffect(() => {
    const stored =
      typeof window !== 'undefined' ? localStorage.getItem(SESSION_KEY) : null

    setLoadingSessions(true)
    loadSessions()
      .then((list) => {
        setLoadingSessions(false)
        if (stored && list.find((s) => s.session_id === stored)) {
          setActiveSessionId(stored)
          loadSessionData(stored)
        } else if (list.length > 0) {
          const id = list[0].session_id
          setActiveSessionId(id)
          localStorage.setItem(SESSION_KEY, id)
          loadSessionData(id)
        }
        // If no sessions exist — show the "Create your first session" empty state
      })
      .catch(() => {
        setLoadingSessions(false)
        setError('Could not reach the server. Make sure it\'s running on port 8001.')
      })
  }, [loadSessions, loadSessionData])

  async function handleCreateSession() {
    setError(null)
    try {
      const s = await createSession()
      setSessions((prev) => [s, ...prev])
      setActiveSessionId(s.session_id)
      setDatasets([])
      setMessages([])
      localStorage.setItem(SESSION_KEY, s.session_id)
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : 'Could not create session. Is the server running?'
      )
    }
  }

  function handleSelectSession(sessionId: string) {
    setActiveSessionId(sessionId)
    localStorage.setItem(SESSION_KEY, sessionId)
    setDatasets([])
    setMessages([])
    loadSessionData(sessionId)
  }

  function handleDatasetAdded(dataset: Dataset) {
    setDatasets((prev) => [...prev, dataset])
  }

  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden">
      {/* Session sidebar */}
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={handleSelectSession}
        onCreate={handleCreateSession}
        loading={loadingSession || loadingSessions}
      />

      {/* Main panel */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header bar */}
        <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between shrink-0">
          <h1 className="text-base font-semibold text-gray-800">Senior Data Analyst</h1>
          <button
            onClick={() => setShowAuditLog(true)}
            className="text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg px-3 py-1 hover:bg-gray-50"
          >
            Audit Log
          </button>
        </div>

        {/* Error banner */}
        {error && (
          <div className="bg-red-50 border-b border-red-200 px-4 py-2 text-sm text-red-700 flex items-center justify-between shrink-0">
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-4 underline text-red-600 hover:text-red-800"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* No session state */}
        {!activeSessionId && !loadingSessions ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <p className="text-gray-500 mb-4">No session selected</p>
              <button
                onClick={handleCreateSession}
                className="rounded-xl bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-700"
              >
                Create Your First Session
              </button>
            </div>
          </div>
        ) : loadingSessions ? (
          /* Session list loading skeleton */
          <div className="flex-1 flex items-center justify-center">
            <div className="flex flex-col items-center gap-3 text-gray-400">
              <div className="w-8 h-8 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin" />
              <p className="text-sm">Loading sessions...</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            {/* Dataset panel */}
            {activeSessionId && (
              <DatasetPanel
                sessionId={activeSessionId}
                datasets={datasets}
                onDatasetAdded={handleDatasetAdded}
              />
            )}

            {/* Chat thread */}
            <div className="flex-1 min-h-0 overflow-hidden">
              {activeSessionId && (
                <ChatThread
                  key={activeSessionId}
                  sessionId={activeSessionId}
                  datasets={datasets.length}
                  initialMessages={messages.map((m) => ({
                    message_id: m.message_id,
                    role: m.role as 'user' | 'assistant',
                    content: m.content,
                    status: m.status,
                  }))}
                />
              )}
            </div>

            {/* Audit log stub button at bottom */}
            <div className="border-t border-gray-200 bg-gray-50 px-4 py-2 shrink-0">
              <button
                onClick={() => setShowAuditLog(true)}
                className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1"
              >
                <span>Audit Log</span>
                <em className="text-gray-300">[STUB: coming in Phase 2]</em>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Audit log drawer */}
      {showAuditLog && <AuditLogDrawer onClose={() => setShowAuditLog(false)} />}
    </div>
  )
}
