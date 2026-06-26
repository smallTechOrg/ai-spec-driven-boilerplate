'use client'

import { useEffect, useState } from 'react'
import { FilePanel } from '@/components/FilePanel'
import { ChatPanel } from '@/components/ChatPanel'
import { DatasetResponse, createSession } from '@/lib/api'

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [datasets, setDatasets] = useState<DatasetResponse[]>([])
  const [activeDatasetId, setActiveDatasetId] = useState<string | null>(null)
  const [sessionError, setSessionError] = useState<string | null>(null)

  useEffect(() => {
    createSession()
      .then((sess) => setSessionId(sess.session_id))
      .catch((err) =>
        setSessionError(
          err instanceof Error ? err.message : 'Failed to create session',
        ),
      )
  }, [])

  function handleDatasetUploaded(ds: DatasetResponse) {
    setDatasets((prev) => [...prev, ds])
    // Auto-select the first uploaded file
    if (!activeDatasetId) setActiveDatasetId(ds.dataset_id)
  }

  if (sessionError) {
    return (
      <main className="flex items-center justify-center h-screen">
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700 max-w-md text-center">
          <p className="font-semibold mb-1">Could not connect to the server</p>
          <p>{sessionError}</p>
          <p className="mt-2 text-xs text-red-500">
            Make sure the FastAPI server is running at port 8001.
          </p>
        </div>
      </main>
    )
  }

  if (!sessionId) {
    return (
      <main className="flex items-center justify-center h-screen">
        <div className="text-sm text-gray-400">Starting session…</div>
      </main>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex-none">
        <h1 className="text-lg font-semibold text-gray-900">Data Analyst Agent</h1>
      </header>

      {/* Two-panel layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left panel */}
        <aside className="w-72 border-r border-gray-200 bg-white flex-none overflow-y-auto">
          <FilePanel
            sessionId={sessionId}
            datasets={datasets}
            activeDatasetId={activeDatasetId}
            onDatasetUploaded={handleDatasetUploaded}
            onSelectDataset={setActiveDatasetId}
          />
        </aside>

        {/* Chat panel */}
        <main className="flex-1 overflow-hidden">
          <ChatPanel
            sessionId={sessionId}
            activeDatasetId={activeDatasetId}
            hasDatasets={datasets.length > 0}
          />
        </main>
      </div>
    </div>
  )
}
