export interface Column {
  name: string
  type: string
}

export interface Dataset {
  dataset_id: string
  name: string
  row_count: number
  columns: Column[]
  uploaded_at: string
}

export interface Session {
  session_id: string
  name: string
  created_at: string
  dataset_count?: number
  message_count?: number
}

export interface Message {
  message_id: string
  role: 'user' | 'assistant'
  content: string
  status: string
  created_at: string
}

export interface QueryResult {
  columns: string[]
  rows: unknown[][]
  row_count: number
}

export interface ChartSpec {
  type: 'bar' | 'line' | 'pie'
  labels: string[]
  datasets: { label: string; data: number[]; backgroundColor?: string | string[] }[]
}

export interface RichResponse {
  narrative: string
  query_result?: QueryResult
  chart_spec?: ChartSpec
  sql?: string
  query_log_id?: string
}

// SSE event types
export type SSEEvent =
  | { type: 'status'; data: { node: string; message: string } }
  | { type: 'chunk'; data: { text: string } }
  | { type: 'table'; data: QueryResult }
  | { type: 'chart'; data: ChartSpec }
  | { type: 'done'; data: { message_id: string; status: string } }
  | { type: 'error'; data: { message: string; node: string } }

const API_BASE = '' // same origin

export async function createSession(): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail?.message ?? `Failed to create session`)
  return { ...data.data, session_id: data.data.session_id }
}

export async function listSessions(): Promise<Session[]> {
  const res = await fetch(`${API_BASE}/sessions`)
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail?.message ?? `Failed to list sessions`)
  return data.data
}

export async function getSession(
  sessionId: string
): Promise<{ session: Session; datasets: Dataset[]; messages: Message[] }> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`)
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail?.message ?? `Session not found`)
  const s = data.data
  return {
    session: { session_id: s.session_id, name: s.name, created_at: s.created_at },
    datasets: s.datasets || [],
    messages: s.messages || [],
  }
}

export async function uploadDataset(sessionId: string, file: File): Promise<Dataset> {
  const formData = new FormData()
  formData.append('session_id', sessionId)
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/datasets`, { method: 'POST', body: formData })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail?.message ?? `Failed to upload dataset`)
  return data.data
}

export function streamChat(
  sessionId: string,
  question: string,
  onEvent: (evt: SSEEvent) => void
): () => void {
  const url = `${API_BASE}/chat?session_id=${encodeURIComponent(sessionId)}&q=${encodeURIComponent(question)}`
  const eventSource = new EventSource(url)

  const handle = (eventType: string) => (e: MessageEvent) => {
    try {
      onEvent({ type: eventType as SSEEvent['type'], data: JSON.parse(e.data) } as SSEEvent)
    } catch {
      // ignore parse errors
    }
  }

  eventSource.addEventListener('status', handle('status'))
  eventSource.addEventListener('chunk', handle('chunk'))
  eventSource.addEventListener('table', handle('table'))
  eventSource.addEventListener('chart', handle('chart'))
  eventSource.addEventListener('done', (e) => {
    handle('done')(e as MessageEvent)
    eventSource.close()
  })
  eventSource.addEventListener('error', (e: Event) => {
    if (e instanceof MessageEvent) {
      handle('error')(e)
    }
    eventSource.close()
  })

  return () => eventSource.close()
}
