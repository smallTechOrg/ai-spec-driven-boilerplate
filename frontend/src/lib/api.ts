// All paths are relative (same origin — served by FastAPI at /app)
// The fetch calls go to / not /app because the static export is at /app but the API is at root.
// We call the API at /sessions not /app/sessions.

export interface SessionResponse {
  session_id: string
  created_at: string
}

export interface DatasetResponse {
  dataset_id: string
  session_id: string
  filename: string
  row_count: number
  column_names: string[]
  created_at: string
}

export interface QueryResponse {
  run_id: string
  status: string
  answer_text: string | null
  table_data: Array<Record<string, unknown>> | null
  chart_b64: string | null
}

export async function createSession(): Promise<SessionResponse> {
  const res = await fetch('/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  })
  if (!res.ok) throw new Error(`Session creation failed (${res.status})`)
  const body = await res.json()
  return body.data
}

export async function uploadDataset(sessionId: string, file: File): Promise<DatasetResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`/sessions/${sessionId}/datasets`, {
    method: 'POST',
    body: form,
  })
  const body = await res.json()
  if (!res.ok) throw new Error(body.detail?.message ?? `Upload failed (${res.status})`)
  return body.data
}

export async function listDatasets(sessionId: string): Promise<DatasetResponse[]> {
  const res = await fetch(`/sessions/${sessionId}/datasets`)
  if (!res.ok) throw new Error(`Failed to list datasets (${res.status})`)
  const body = await res.json()
  return body.data.datasets
}

export async function runQuery(
  sessionId: string,
  datasetId: string,
  question: string,
): Promise<QueryResponse> {
  const res = await fetch(`/sessions/${sessionId}/queries`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, dataset_id: datasetId }),
  })
  const body = await res.json()
  if (!res.ok) throw new Error(body.detail?.message ?? `Query failed (${res.status})`)
  return body.data
}
