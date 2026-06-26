'use client'

import { useCallback, useState } from 'react'
import { SessionSidebar } from '@/components/analyse/SessionSidebar'
import { TokenWidget } from '@/components/analyse/TokenWidget'
import { TablesCard } from '@/components/analyse/TablesCard'
import { UploadCard } from '@/components/analyse/UploadCard'
import { ConversationCard } from '@/components/analyse/ConversationCard'

/** Token counts from the most recent completed ask (drives the TokenWidget). */
export interface LastQueryTokens {
  input: number
  output: number
}

/**
 * Analyse tab — the real Phase-2 surface.
 *
 * Owns the small slice of shared state the three real cards coordinate on:
 *  - `selectedDatasetId`  : the single active dataset for asking (Phase 2 is
 *    single-dataset; the radio in the Tables card sets it).
 *  - `datasetsVersion`    : a monotonically-increasing token; bumping it tells
 *    the Tables card to re-fetch /datasets (after each upload / completed ask).
 *  - `lastTokens`         : in/out tokens from the latest answer, shown by the
 *    Token widget's (real) "Last query" row.
 *
 * Layout: a left sidebar (sessions stub + token usage) and a main column
 * (tables, upload, conversation). Stacks on narrow viewports.
 */
export function AnalyseTab({ provider }: { provider?: string }) {
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null)
  const [datasetsVersion, setDatasetsVersion] = useState(0)
  const [lastTokens, setLastTokens] = useState<LastQueryTokens | null>(null)

  const refreshDatasets = useCallback(() => {
    setDatasetsVersion(v => v + 1)
  }, [])

  // When a dataset is deleted, clear the selection if it was the active one.
  const handleDatasetDeleted = useCallback(
    (deletedId: string) => {
      setSelectedDatasetId(prev => (prev === deletedId ? null : prev))
      refreshDatasets()
    },
    [refreshDatasets],
  )

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[20rem_1fr]">
      {/* Sidebar */}
      <aside className="flex flex-col gap-4">
        <SessionSidebar />
        <TokenWidget provider={provider} lastTokens={lastTokens} />
      </aside>

      {/* Main column */}
      <div className="flex flex-col gap-4">
        <TablesCard
          datasetsVersion={datasetsVersion}
          selectedDatasetId={selectedDatasetId}
          onSelect={setSelectedDatasetId}
          onDeleted={handleDatasetDeleted}
        />
        <UploadCard onUploaded={refreshDatasets} />
        <ConversationCard
          selectedDatasetId={selectedDatasetId}
          onAnswered={tokens => {
            setLastTokens(tokens)
            refreshDatasets()
          }}
        />
      </div>
    </div>
  )
}
