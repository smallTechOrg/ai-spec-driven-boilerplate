// Typed fetch helpers + response types for the Local Data Analyst API.
//
// The UI is a Next.js static export served by FastAPI at `/app/`, calling the
// REST API under `/api/...` on the same origin. All paths here are ABSOLUTE
// from the origin root (e.g. `/api/datasets`) so they resolve correctly when
// the page itself is served at `/app/`.
//
// Shapes match spec/api.md exactly (the binding contract). Success responses
// use the envelope `{ data, error }`; transport failures return an HTTP error
// status with `{ detail: { code, message } }`.

// ---------------------------------------------------------------------------
// Contract types (spec/api.md)
// ---------------------------------------------------------------------------

export interface ProfileColumn {
  name: string
  type: string
  null_count: number
  min?: number | null
  max?: number | null
  mean?: number | null
}

export interface DatasetProfile {
  row_count: number
  columns: ProfileColumn[]
}

export interface Dataset {
  id: string
  name: string
  source_kind: string
  sheet_name: string | null
  row_count: number
  profile: DatasetProfile
}

export interface UploadResult {
  datasets: Dataset[]
}

export interface KeyStat {
  label: string
  value: string | number
  unit?: string | null
}

export type ChartType = 'bar' | 'line' | 'pie'

export interface ChartSpec {
  type: ChartType
  x: string
  y: string
  series?: string | null
  // Each row is an object keyed by the column names referenced in x / y / series.
  data: Array<Record<string, string | number | null>>
}

export interface SummaryTable {
  columns: string[]
  rows: Array<Array<string | number | null>>
}

export interface AskCost {
  prompt_tokens: number
  completion_tokens: number
  est_usd: number
}

export type RunStatus = 'completed' | 'failed' | 'pending' | 'running'

export interface AskResult {
  run_id: string
  status: RunStatus
  answer: string
  key_stats: KeyStat[]
  chart_spec: ChartSpec | null
  summary_table: SummaryTable | null
  insight: string
  follow_ups: string[]
  plan_steps: string[]
  generated_sql: string
  cost: AskCost
  // On a failed run (HTTP 200, status:"failed") the backend includes an error
  // message inside `data` so the UI can show what was tried.
  error?: string | null
}

export interface RunSummary {
  id: string
  dataset_id: string
  status: RunStatus
  question: string
  generated_sql: string
  est_usd: number
  created_at: string
}

export interface RunsResult {
  runs: RunSummary[]
}

// ---------------------------------------------------------------------------
// Error handling
// ---------------------------------------------------------------------------

/** A transport / HTTP-level failure carrying the server's `{code, message}`. */
export class ApiError extends Error {
  code: string
  status: number
  constructor(code: string, message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

/** A network-level failure (server unreachable). */
export class NetworkError extends Error {
  constructor(message = 'Network error — is the server running?') {
    super(message)
    this.name = 'NetworkError'
  }
}

interface Envelope<T> {
  data: T
  error: string | null
}

async function parseJson(res: Response): Promise<unknown> {
  try {
    return await res.json()
  } catch {
    return null
  }
}

async function handle<T>(res: Response): Promise<T> {
  const body = await parseJson(res)
  if (!res.ok) {
    const detail =
      body && typeof body === 'object' && 'detail' in body
        ? (body as { detail?: { code?: string; message?: string } }).detail
        : undefined
    throw new ApiError(
      detail?.code ?? 'error',
      detail?.message ?? `Request failed (${res.status})`,
      res.status,
    )
  }
  const env = body as Envelope<T> | null
  if (!env || env.data === undefined || env.data === null) {
    throw new ApiError('bad_response', 'Malformed response from server.', res.status)
  }
  return env.data
}

function isNetworkFailure(err: unknown): boolean {
  return err instanceof TypeError
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

/** Upload one CSV/Excel file. Each Excel sheet becomes its own dataset. */
export async function uploadDataset(file: File): Promise<UploadResult> {
  const form = new FormData()
  form.append('file', file)
  let res: Response
  try {
    res = await fetch('/api/datasets', { method: 'POST', body: form })
  } catch (err) {
    if (isNetworkFailure(err)) throw new NetworkError()
    throw err
  }
  return handle<UploadResult>(res)
}

/** Ask a plain-English question of a loaded dataset. */
export async function ask(datasetId: string, question: string): Promise<AskResult> {
  let res: Response
  try {
    res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_id: datasetId, question }),
    })
  } catch (err) {
    if (isNetworkFailure(err)) throw new NetworkError()
    throw err
  }
  // A failed run is HTTP 200 with status:"failed" — it flows through `handle`
  // normally and is rendered transparently by the caller.
  return handle<AskResult>(res)
}

/** List the audit history (most recent first). */
export async function listRuns(): Promise<RunsResult> {
  let res: Response
  try {
    res = await fetch('/api/runs')
  } catch (err) {
    if (isNetworkFailure(err)) throw new NetworkError()
    throw err
  }
  return handle<RunsResult>(res)
}

/** Normalise any thrown error into a user-facing message. */
export function errorMessage(err: unknown): string {
  if (err instanceof NetworkError) return err.message
  if (err instanceof ApiError) return err.message
  if (err instanceof Error) return err.message
  return 'Something went wrong.'
}
