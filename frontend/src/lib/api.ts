// API client for DataChat.
//
// The Next.js app is served same-origin by FastAPI under `/app/`, but the API
// routes live at the server root (`/datasets`, `/runs`, ...). We therefore call
// ROOT-RELATIVE paths (leading slash, no host, NOT prefixed with the `/app`
// basePath) so requests resolve to the FastAPI routes regardless of where the
// static bundle is mounted.
//
// Every JSON response uses the skeleton envelope `{ data, error }`; success
// payloads live under `data`. Errors come back as `{ detail: { code, message } }`
// with a non-2xx status. `unwrap` normalises both into a thrown ApiError or the
// inner `data`.

export class ApiError extends Error {
  code: string
  status: number
  constructor(message: string, code: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

async function unwrap<T>(res: Response): Promise<T> {
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    // Non-JSON body (e.g. a proxy error page).
    throw new ApiError(
      `The server returned an unexpected response (${res.status}).`,
      'bad_response',
      res.status,
    )
  }

  if (!res.ok) {
    const detail = (body as { detail?: { code?: string; message?: string } } | null)?.detail
    throw new ApiError(
      detail?.message ?? `Request failed (${res.status}).`,
      detail?.code ?? 'http_error',
      res.status,
    )
  }

  const envelope = body as { data?: T; error?: string | null }
  if (envelope?.error) {
    throw new ApiError(envelope.error, 'envelope_error', res.status)
  }
  return envelope.data as T
}

// ---- Domain types (mirror spec/api.md) ---------------------------------------

export interface ProfileColumn {
  name: string
  dtype: string
  non_null: number
  n_unique: number
  min: string | number | null
  max: string | number | null
  sample_values: (string | number | null)[]
}

export interface DatasetProfile {
  columns: ProfileColumn[]
  row_count: number
  quality_flags?: string[]
}

export interface Dataset {
  id: string
  name: string
  kind: string
  row_count: number
  column_count: number
  size_bytes?: number
  created_at: string
}

export interface DatasetBundle {
  dataset: Dataset
  profile: DatasetProfile
}

export interface TokenUsage {
  prompt: number
  completion: number
  total: number
}

export interface AnalysisRun {
  id: string
  question: string
  answer: string | null
  code: string | null
  result_summary?: string | null
  tokens?: TokenUsage | null
  cost_usd?: number | null
  status: 'succeeded' | 'failed' | string
  error_message?: string | null
  assumptions?: string[] | null
  followups?: string[] | null
  viz?: unknown | null
  steps?: { step_index: number; phase: string; code?: string; error?: string }[] | null
  created_at: string
  completed_at?: string | null
}

// ---- Calls (Phase 1) ---------------------------------------------------------

export async function uploadDataset(file: File, name?: string): Promise<DatasetBundle> {
  const form = new FormData()
  form.append('file', file)
  if (name) form.append('name', name)
  const res = await fetch('/datasets', { method: 'POST', body: form })
  return unwrap<DatasetBundle>(res)
}

export async function getDataset(id: string): Promise<DatasetBundle> {
  const res = await fetch(`/datasets/${encodeURIComponent(id)}`)
  return unwrap<DatasetBundle>(res)
}

export async function askDataset(id: string, question: string): Promise<{ run: AnalysisRun }> {
  const res = await fetch(`/datasets/${encodeURIComponent(id)}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  return unwrap<{ run: AnalysisRun }>(res)
}

export async function getRun(id: string): Promise<{ run: AnalysisRun }> {
  const res = await fetch(`/runs/${encodeURIComponent(id)}`)
  return unwrap<{ run: AnalysisRun }>(res)
}
