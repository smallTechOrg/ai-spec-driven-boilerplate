import { DataTable } from './DataTable'

export type Message = {
  id: string
  role: 'user' | 'assistant'
  text: string | null
  tableData: Array<Record<string, unknown>> | null
  error?: string | null
  thinking?: boolean
}

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end mb-3">
        <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-blue-600 px-4 py-3 text-sm text-white shadow-sm">
          {message.text}
        </div>
      </div>
    )
  }

  // Assistant bubble
  return (
    <div className="flex justify-start mb-3">
      <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-white border border-gray-200 px-4 py-3 text-sm text-gray-800 shadow-sm">
        {message.thinking ? (
          <div className="flex items-center gap-1.5 text-gray-500">
            <span className="inline-block w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.32s]" />
            <span className="inline-block w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.16s]" />
            <span className="inline-block w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
          </div>
        ) : message.error ? (
          <p className="text-red-600">Something went wrong: {message.error}</p>
        ) : (
          <>
            {message.text && (
              <div className="whitespace-pre-wrap leading-relaxed">{message.text}</div>
            )}
            {message.tableData && message.tableData.length > 0 && (
              <DataTable data={message.tableData} />
            )}
            {/* Phase 2 stub — clearly labelled, always shown in Phase 1 assistant bubbles */}
            <div className="mt-3 rounded border border-dashed border-amber-300 bg-amber-50 px-3 py-2">
              <p className="text-xs font-medium text-amber-700">Charts coming in Phase 2</p>
              <p className="text-xs text-amber-600">— not yet active</p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
