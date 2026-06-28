// API client + types for the data-analysis agent.
// Single-origin: the static export is served by FastAPI at /app, the API lives at /api on
// the same origin, so relative paths work in production. For inner-loop `pnpm dev` we fall
// back to the documented backend origin.

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ??
  (typeof window !== 'undefined' && window.location.port === '3000'
    ? 'http://localhost:8001'
    : '')

export interface ProfileColumn {
  name: string
  dtype: string
  missing_count: number
  distinct_count?: number
  top_values?: (string | number)[]
  min?: number
  max?: number
  mean?: number
}

export interface DatasetProfile {
  columns: ProfileColumn[]
  sample: Record<string, unknown>[]
}

export interface Dataset {
  id: string
  filename: string
  row_count: number
  column_count: number
  size_bytes: number
  profile: DatasetProfile
}

export interface Analysis {
  id: string
  dataset_id: string
  question: string
  status: 'completed' | 'failed'
  answer?: string
  result?: unknown
  chart_spec?: Record<string, unknown> | null
  code?: string
  steps_taken?: number
  error_message?: string
  created_at?: string
}

class ApiError extends Error {}

async function detail(res: Response): Promise<string> {
  try {
    const body = await res.json()
    return body?.detail ?? `Request failed (${res.status})`
  } catch {
    return `Request failed (${res.status})`
  }
}

export async function uploadDataset(file: File): Promise<Dataset> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/api/datasets`, { method: 'POST', body: form })
  if (!res.ok) throw new ApiError(await detail(res))
  return res.json()
}

export async function runAnalysis(datasetId: string, question: string): Promise<Analysis> {
  const res = await fetch(`${API_BASE}/api/analyses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataset_id: datasetId, question }),
  })
  if (!res.ok) throw new ApiError(await detail(res))
  return res.json()
}

export function formatBytes(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(i ? 1 : 0)} ${units[i]}`
}
