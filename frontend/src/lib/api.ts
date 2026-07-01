// Call the API on the same origin the page is served from (FastAPI serves both
// the UI at /app/ and the API at /sessions). Works deployed and when served
// locally via `python -m src`. Override with NEXT_PUBLIC_API_URL for `pnpm dev`.
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ??
  (typeof window !== "undefined" ? window.location.origin : "http://localhost:8001");

export interface ColumnProfile {
  name: string;
  dtype: string;
  null_count: number;
  null_pct: number;
  sample_values: string[];
  stats?: { min: number; max: number; mean: number; std: number; p25: number; p50: number; p75: number };
  value_counts?: Record<string, number>;
}

export interface QualityFlag {
  type: "WARNING" | "ERROR" | "INFO";
  column: string | null;
  message: string;
}

export interface FileProfile {
  row_count: number;
  column_count: number;
  columns: ColumnProfile[];
  quality_flags: QualityFlag[];
}

export interface UploadedFile {
  file_id: string;
  filename: string;
  profile: FileProfile;
}

export interface QualityIssue {
  type: "WARNING" | "INFO" | "ERROR";
  category: "missing_values" | "type_mismatch" | "invalid_dates" | "outliers" | "duplicates";
  column: string | null;
  detail: string;
}

export interface QualityFileReport {
  filename: string;
  issues: QualityIssue[];
  duplicate_rows_removed: number;
}

export interface QualityReport {
  has_issues: boolean;
  files: QualityFileReport[];
  clean_actions: string[];
}

export interface Message {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  chart_json: Record<string, unknown> | null;
  created_at?: string;
  action?: string;  // "answer" | "clarification" | "error"
  quality_report?: QualityReport | null;
}

export async function createSession(): Promise<string> {
  const res = await fetch(`${API_BASE}/sessions`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to create session");
  const body = await res.json();
  return body.data.session_id;
}

export async function uploadFile(sessionId: string, file: File): Promise<UploadedFile> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/files`, { method: "POST", body: form });
  const body = await res.json();
  if (!res.ok) throw new Error(body.error?.message ?? "Upload failed");
  return body.data;
}

export async function sendMessage(sessionId: string, content: string): Promise<Message> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body.error?.message ?? "Failed to send message");
  return body.data;
}

export async function getMessages(sessionId: string): Promise<Message[]> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`);
  const body = await res.json();
  if (!res.ok) throw new Error(body.error?.message ?? "Failed to get messages");
  return body.data.messages;
}

export async function exportResult(sessionId: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/export`, { method: "POST" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error?.message ?? "Export failed — no exportable result from the last query");
  }
  return res.blob();
}
