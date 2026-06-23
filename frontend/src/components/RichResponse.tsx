'use client'

import DataTable from './DataTable'
import AnalystChart from './AnalystChart'
import type { QueryResult, ChartSpec } from '../lib/api'

interface RichResponseData {
  narrative?: string
  query_result?: QueryResult
  chart_spec?: ChartSpec
  sql?: string
}

interface Props {
  response: RichResponseData
  isStreaming?: boolean
}

// Lightweight markdown renderer — handles **bold**, `code`, and newlines.
// Returns an array of React elements.
function renderMarkdown(text: string): React.ReactNode[] {
  return text.split('\n').map((line, i) => {
    if (!line.trim()) return <br key={i} />

    // Split on **bold** and `code` patterns
    const parts = line.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)

    return (
      <p key={i} className="mb-1 last:mb-0">
        {parts.map((part, j) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return <strong key={j}>{part.slice(2, -2)}</strong>
          }
          if (part.startsWith('`') && part.endsWith('`')) {
            return (
              <code key={j} className="bg-gray-100 px-1 rounded text-xs font-mono">
                {part.slice(1, -1)}
              </code>
            )
          }
          return <span key={j}>{part}</span>
        })}
      </p>
    )
  })
}

export default function RichResponse({ response, isStreaming }: Props) {
  return (
    <div className="space-y-3">
      {response.narrative && (
        <div className="text-sm text-gray-800 leading-relaxed">
          {renderMarkdown(response.narrative)}
          {isStreaming && (
            <span className="inline-block w-1 h-4 bg-blue-500 animate-pulse ml-1 align-middle" />
          )}
        </div>
      )}

      {response.query_result && <DataTable result={response.query_result} />}

      {response.chart_spec && <AnalystChart spec={response.chart_spec} />}

      {response.sql && (
        <details className="mt-2">
          <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600 select-none">
            View SQL
          </summary>
          <pre className="mt-1 rounded bg-gray-900 text-gray-100 p-3 text-xs overflow-x-auto font-mono whitespace-pre-wrap">
            {response.sql}
          </pre>
        </details>
      )}
    </div>
  )
}
