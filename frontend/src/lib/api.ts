// API client + types for the data-analyst agent.
//
// IMPORTANT: the static UI is served at /app/ by FastAPI on the SAME origin,
// but the REST API lives at the ROOT (/datasets, ...). Next.js `basePath: '/app'`
// only rewrites router links/asset URLs — it does NOT touch raw fetch() strings.
// So absolute-from-root paths like '/datasets' correctly hit the FastAPI root,
// not /app/datasets. We keep them root-relative on purpose.

export interface ColumnProfile {
  name: string
  dtype: string
  distinct_count: number
  null_count: number
  sample_values: unknown[]
}

export interface DatasetProfile {
  dataset_id: string
  name: string
  row_count: number
  column_count: number
  profile: ColumnProfile[]
  sample_rows: Record<string, unknown>[]
}

export interface ChartSpec {
  chart_type: string
  x: string
  y: string
  title?: string
}

export interface TokenUsage {
  prompt: number
  completion: number
  total: number
}

export interface AnswerData {
  turn_id: string
  conversation_id: string
  answer: string
  plan: string[]
  code: string
  result_table: Record<string, unknown>[]
  chart_spec: ChartSpec | null
  follow_ups: string[]
  token_usage: TokenUsage
  estimated_cost_usd: number
  assumptions: string[]
}

export type StepName = 'plan' | 'generate_code' | 'execute_local' | 'visualize'
export type StepStatus = 'pending' | 'running' | 'done' | 'error'

export const STEP_ORDER: { key: StepName; label: string }[] = [
  { key: 'plan', label: 'Plan' },
  { key: 'generate_code', label: 'Generate code' },
  { key: 'execute_local', label: 'Execute locally' },
  { key: 'visualize', label: 'Visualize' },
]

function errorMessageFromBody(body: unknown, status: number): string {
  if (body && typeof body === 'object') {
    const b = body as Record<string, unknown>
    const detail = b.detail
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object') {
      const msg = (detail as Record<string, unknown>).message
      if (typeof msg === 'string') return msg
    }
    if (typeof b.message === 'string') return b.message
  }
  return `Request failed (${status})`
}

export async function uploadDataset(file: File): Promise<DatasetProfile> {
  const form = new FormData()
  form.append('file', file)
  let res: Response
  try {
    res = await fetch('/datasets', { method: 'POST', body: form })
  } catch {
    throw new Error('Network error — is the server running?')
  }
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    /* non-JSON */
  }
  if (!res.ok) throw new Error(errorMessageFromBody(body, res.status))
  const data = (body as { data?: DatasetProfile })?.data
  if (!data) throw new Error('Unexpected response from server.')
  return data
}

/**
 * Ask a question. Consumes the SSE step stream to drive live status, then
 * resolves with the final AnswerData.
 *
 * The endpoint streams `text/event-stream`. Each event payload is a JSON line.
 * Step events look like {"step":"plan","status":"running"}. The final payload
 * is the full answer envelope {"data": {...}} (it carries `turn_id`/`answer`).
 * We parse incrementally from the ReadableStream reader. If the server instead
 * returns a plain JSON body (no streaming), we fall back to a single parse.
 */
export async function askQuestion(
  datasetId: string,
  question: string,
  conversationId: string | null,
  onStep: (step: StepName, status: StepStatus) => void,
): Promise<AnswerData> {
  let res: Response
  try {
    res = await fetch(`/datasets/${datasetId}/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({ question, conversation_id: conversationId }),
    })
  } catch {
    throw new Error('Network error — is the server running?')
  }

  if (!res.ok) {
    let body: unknown = null
    try {
      body = await res.json()
    } catch {
      /* ignore */
    }
    throw new Error(errorMessageFromBody(body, res.status))
  }

  const contentType = res.headers.get('content-type') ?? ''

  // Non-streaming fallback: a plain JSON answer envelope.
  if (!res.body || !contentType.includes('text/event-stream')) {
    const body = (await res.json()) as { data?: AnswerData }
    if (!body?.data) throw new Error('Unexpected response from server.')
    return body.data
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalAnswer: AnswerData | null = null

  const handlePayload = (raw: string) => {
    const text = raw.trim()
    if (!text) return
    let parsed: unknown
    try {
      parsed = JSON.parse(text)
    } catch {
      return
    }
    if (parsed && typeof parsed === 'object') {
      const obj = parsed as Record<string, unknown>
      if (obj.data && typeof obj.data === 'object') {
        finalAnswer = obj.data as AnswerData
        return
      }
      if (typeof obj.step === 'string') {
        onStep(obj.step as StepName, (obj.status as StepStatus) ?? 'running')
        return
      }
      // Bare answer object (no envelope) — detect by turn_id/answer.
      if ('answer' in obj || 'turn_id' in obj) {
        finalAnswer = obj as unknown as AnswerData
      }
    }
  }

  // SSE frames are separated by a blank line; each `data:` line holds payload.
  const flushFrames = () => {
    let sep: number
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      const dataLines = frame
        .split('\n')
        .filter(l => l.startsWith('data:'))
        .map(l => l.slice(5).trimStart())
      if (dataLines.length) {
        handlePayload(dataLines.join('\n'))
      } else {
        // Some servers stream raw JSON lines without the `data:` prefix.
        handlePayload(frame)
      }
    }
  }

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    flushFrames()
  }
  buffer += decoder.decode()
  // Process any trailing frame without a terminating blank line.
  if (buffer.trim()) {
    buffer += '\n\n'
    flushFrames()
  }

  if (!finalAnswer) {
    throw new Error('The agent did not return an answer. Please try again.')
  }
  return finalAnswer
}

export function formatCost(usd: number): string {
  if (usd === 0) return '$0.0000'
  if (usd < 0.01) return `$${usd.toFixed(4)}`
  return `$${usd.toFixed(2)}`
}
