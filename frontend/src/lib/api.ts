// Same-origin fetch helpers for the data-analyst API.
// The UI is served at /app/ but the API is mounted at root, so paths are absolute-from-root.

export interface Column {
  name: string
  type: string
}

export interface Dataset {
  id: string
  name: string
  table_name: string
  row_count: number
  columns: Column[]
  created_at: string
}

export interface Query {
  id: string
  dataset_id: string
  question: string
  generated_sql: string | null
  answer_text: string | null
  result_columns: string[]
  result_rows: (string | number | null)[][]
  row_count: number
  status: string
  error: string | null
  created_at: string
}

export interface AuditEntry {
  id: string
  operation: string
  dataset_id: string | null
  query_id: string | null
  sql_text: string | null
  row_count: number | null
  columns: string[] | null
  duration_ms: number | null
  success: boolean
  error_message: string | null
  created_at: string
}

class ApiError extends Error {
  code: string
  constructor(code: string, message: string) {
    super(message)
    this.code = code
    this.name = 'ApiError'
  }
}

async function unwrap<T>(res: Response): Promise<T> {
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    // fall through to status-based error below
  }
  if (!res.ok) {
    const detail = (body as { detail?: { code?: string; message?: string } } | null)?.detail
    throw new ApiError(
      detail?.code ?? 'HTTP_ERROR',
      detail?.message ?? `Request failed (${res.status})`,
    )
  }
  return (body as { data: T }).data
}

export async function listDatasets(): Promise<Dataset[]> {
  return unwrap<Dataset[]>(await fetch('/datasets'))
}

export async function uploadDataset(file: File, name?: string): Promise<Dataset> {
  const form = new FormData()
  form.append('file', file)
  if (name) form.append('name', name)
  return unwrap<Dataset>(await fetch('/datasets', { method: 'POST', body: form }))
}

export async function listQueries(datasetId: string): Promise<Query[]> {
  const params = new URLSearchParams({ dataset_id: datasetId })
  return unwrap<Query[]>(await fetch(`/queries?${params.toString()}`))
}

export async function askQuery(datasetId: string, question: string): Promise<Query> {
  return unwrap<Query>(
    await fetch('/queries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_id: datasetId, question }),
    }),
  )
}

export async function listAudit(limit = 100): Promise<AuditEntry[]> {
  const params = new URLSearchParams({ limit: String(limit) })
  return unwrap<AuditEntry[]>(await fetch(`/audit?${params.toString()}`))
}

export { ApiError }
