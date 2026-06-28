// API client for the data-analysis workbench.
//
// IMPORTANT path note: the UI is served at http://localhost:8001/app/ (basePath '/app'),
// but the API routes are mounted at the SERVER ROOT (http://localhost:8001/datasets, /ask).
// Next's basePath rewrites in-app links, but a raw fetch() does NOT get basePath prefixed —
// a root-absolute path like fetch('/datasets') resolves against the page ORIGIN
// (http://localhost:8001) and hits the API root, not /app/datasets. That is exactly what we want.
// We therefore use root-absolute, same-origin paths and never hardcode a host.

export interface ProfileColumn {
  name: string
  dtype: string
  missing: number
  distinct: number
  top?: (string | number)[]
}

export interface NumericStat {
  min: number
  max: number
  mean: number
}

export interface DatasetProfile {
  columns: ProfileColumn[]
  numeric_stats: Record<string, NumericStat>
  sample: Record<string, unknown>[]
}

export interface Dataset {
  id: string
  name: string
  file_type: string
  row_count: number
  size_bytes: number
  profile: DatasetProfile
  created_at: string
}

export interface AskResponse {
  run_id: string
  conversation_id: string
  status: string
  answer: string
  plan: string
  code: string
  result_preview: string
  iterations: number
  suggestions: string[]
  chart_spec: unknown | null
  clarifying_question: string | null
  tokens?: { prompt: number; completion: number }
  cost_usd?: number
}

export class ApiError extends Error {
  code?: string
  status: number
  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

// Pull a human message out of either the error envelope or a raw body.
function extractError(body: unknown, status: number): ApiError {
  if (body && typeof body === 'object') {
    const b = body as Record<string, unknown>
    const detail = b.detail as Record<string, unknown> | undefined
    if (detail && typeof detail === 'object') {
      const msg = (detail.message as string) ?? (detail.code as string)
      if (msg) return new ApiError(msg, status, detail.code as string | undefined)
    }
    if (typeof b.error === 'string') return new ApiError(b.error, status)
    const data = b.data as Record<string, unknown> | undefined
    if (data && typeof data.error === 'string') return new ApiError(data.error as string, status)
  }
  return new ApiError(`Request failed (${status})`, status)
}

async function parseJson(res: Response): Promise<unknown> {
  try {
    return await res.json()
  } catch {
    return null
  }
}

export async function uploadDataset(file: File): Promise<Dataset> {
  const form = new FormData()
  form.append('file', file)
  let res: Response
  try {
    // root-absolute -> http://localhost:8001/datasets
    res = await fetch('/datasets', { method: 'POST', body: form })
  } catch {
    throw new ApiError('Network error — is the server running?', 0)
  }
  const body = await parseJson(res)
  if (!res.ok) throw extractError(body, res.status)
  return (body as { data: Dataset }).data
}

export async function ask(
  datasetId: string,
  question: string,
  conversationId: string | null,
): Promise<AskResponse> {
  let res: Response
  try {
    // root-absolute -> http://localhost:8001/ask
    res = await fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dataset_id: datasetId,
        question,
        conversation_id: conversationId,
      }),
    })
  } catch {
    throw new ApiError('Network error — is the server running?', 0)
  }
  const body = await parseJson(res)
  if (!res.ok) throw extractError(body, res.status)
  return (body as { data: AskResponse }).data
}
