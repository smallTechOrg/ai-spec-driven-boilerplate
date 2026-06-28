// Type definitions and fetch wrappers for the Data Analysis Agent API

export interface SchemaPreview {
  columns: string[]
  dtypes: Record<string, string>
  sample_rows: (string | number | null)[][]
}

export interface UploadedFile {
  file_id: string
  original_name: string
  source_type: string
  row_count: number | null
  file_size_bytes: number | null
  schema_preview: SchemaPreview
}

export interface ChartSpec {
  chart_type: string
  data: Record<string, unknown>[]
  layout: Record<string, unknown>
}

export interface AnalysisResult {
  run_id: string
  answer: string | null
  chart_spec: ChartSpec | null
  status: string
  error?: string
}

export async function uploadFile(file: File): Promise<UploadedFile> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch('/api/files/upload', { method: 'POST', body: formData })
  const json = await res.json()
  if (!res.ok || !json.ok) throw new Error(json.error?.message ?? `Upload failed (${res.status})`)
  return json.data
}

export async function listFiles(): Promise<UploadedFile[]> {
  const res = await fetch('/api/files')
  const json = await res.json()
  if (!res.ok) throw new Error(json.error?.message ?? 'Failed to load files')
  return json.data.files
}

export async function runAnalysis(fileId: string, question: string): Promise<AnalysisResult> {
  const res = await fetch('/api/analysis/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: fileId, question }),
  })
  const json = await res.json()
  if (!res.ok) throw new Error(json.error?.message ?? `Analysis failed (${res.status})`)
  return json.data
}
