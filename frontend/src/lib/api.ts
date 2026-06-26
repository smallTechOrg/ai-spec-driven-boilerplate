/**
 * API helper for the Data Analysis Agent frontend.
 *
 * The backend (FastAPI) is served single-origin: the UI lives under `/app/`,
 * the API at the origin root. All fetches here use ROOT-RELATIVE paths
 * (e.g. "/health", "/upload") which resolve to the origin root regardless of
 * the `/app` basePath — so the same build works in dev and in the bundled
 * single-origin server.
 *
 * Envelope contract (spec/api.md):
 *   success: { "data": <payload>, "error": null }   (HTTP 2xx)
 *   error:   { "detail": { "code": <str>, "message": <str> } }   (HTTP 4xx/5xx)
 *
 * `unwrap()` returns the success payload and throws an `ApiError` carrying the
 * `code` + `message` on the error shape, so callers can branch on
 * `err.code === "duplicate_dataset"` etc.
 */

/** Error thrown for any non-2xx response, carrying the contract's code/message. */
export class ApiError extends Error {
  code: string
  status: number
  /** The raw `detail` object (may carry extra fields like `existing_*`). */
  detail: Record<string, unknown> | null

  constructor(
    code: string,
    message: string,
    status: number,
    detail: Record<string, unknown> | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.detail = detail
  }
}

/** Parse a fetch Response per the envelope contract; throw ApiError on failure. */
async function unwrap<T>(res: Response): Promise<T> {
  let body: unknown = null
  const text = await res.text()
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      // Non-JSON body (e.g. a proxy error page) — fall through to a generic error.
      body = null
    }
  }

  if (!res.ok) {
    const detail =
      body && typeof body === 'object' && 'detail' in body
        ? (body as { detail: unknown }).detail
        : null

    if (detail && typeof detail === 'object') {
      const d = detail as Record<string, unknown>
      const code = typeof d.code === 'string' ? d.code : 'error'
      const message =
        typeof d.message === 'string' ? d.message : `Request failed (${res.status})`
      throw new ApiError(code, message, res.status, d)
    }

    // Fallback when the error body isn't in the documented shape.
    const message =
      typeof detail === 'string' ? detail : `Request failed (${res.status})`
    throw new ApiError('error', message, res.status, null)
  }

  // Success: unwrap { data, error } when present, else return the raw body.
  if (body && typeof body === 'object' && 'data' in body) {
    return (body as { data: T }).data
  }
  return body as T
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path, { method: 'GET', headers: { Accept: 'application/json' } })
  return unwrap<T>(res)
}

async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(payload),
  })
  return unwrap<T>(res)
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(path, { method: 'DELETE', headers: { Accept: 'application/json' } })
  return unwrap<T>(res)
}

// ---------------------------------------------------------------------------
// Response types (subset of spec/api.md needed in Phase 2)
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string
  provider: string
}

export interface UploadResponse {
  dataset_id: string
  filename: string
  format: string
  row_count: number
  col_count: number
  columns: string[]
  context: string | null
  auto_notes_status: string | null
}

export interface DatasetSummary {
  id: string
  filename: string
  row_count: number
  col_count: number
  format: string
  origin: string
  stale?: boolean
  [key: string]: unknown
}

export interface ColumnSchema {
  name: string
  dtype: string
}

export interface DatasetDetail extends DatasetSummary {
  columns_schema: ColumnSchema[]
  context: string | null
  derivation_code: string | null
  auto_notes_status: string | null
}

export interface PreviewResponse {
  columns: string[]
  rows: unknown[][]
}

export interface AskStep {
  action: string
  result: string
  is_error: boolean
}

export interface AskResponse {
  type: string
  run_id: string
  session_id?: string | null
  dataset_ids: string[]
  datasets_used?: string[]
  answer_markdown: string
  answer_html?: string
  iteration_count: number
  tokens_input: number
  tokens_output: number
  status: string
  is_best_effort: boolean
  steps: AskStep[]
  suggested_questions: string[]
  prompt_breakdown?: Record<string, unknown>
  // Clarification variant (Phase 3 — handled defensively here):
  clarification_question?: string
}

export interface CurrentRun {
  run_id: string | null
  status: string
  iteration_count: number
  max_iterations: number
}

// ---------------------------------------------------------------------------
// Endpoint wrappers (Phase 2 surface)
// ---------------------------------------------------------------------------

export const api = {
  health: () => getJson<HealthResponse>('/health'),

  /**
   * POST /upload — multipart `file`, optional `context`, optional `?force=true`.
   * On a duplicate the server returns 409 with code `duplicate_dataset`; this
   * surfaces as an `ApiError` the caller can branch on.
   */
  async upload(
    file: File,
    opts: { context?: string; force?: boolean } = {},
  ): Promise<UploadResponse> {
    const form = new FormData()
    form.append('file', file)
    if (opts.context && opts.context.trim()) {
      form.append('context', opts.context.trim())
    }
    const path = opts.force ? '/upload?force=true' : '/upload'
    const res = await fetch(path, { method: 'POST', body: form })
    return unwrap<UploadResponse>(res)
  },

  listDatasets: () => getJson<DatasetSummary[]>('/datasets'),

  getDataset: (id: string) => getJson<DatasetDetail>(`/datasets/${encodeURIComponent(id)}`),

  preview: (id: string, rows = 10) =>
    getJson<PreviewResponse>(`/datasets/${encodeURIComponent(id)}/preview?rows=${rows}`),

  deleteDataset: (id: string) => del<unknown>(`/datasets/${encodeURIComponent(id)}`),

  ask: (datasetId: string, question: string) =>
    postJson<AskResponse>('/ask', { dataset_id: datasetId, question }),

  currentRun: () => getJson<CurrentRun>('/runs/current'),
}
