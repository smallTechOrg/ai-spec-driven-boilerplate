export interface ColumnDef {
  name: string;
  type: string;
}

export interface DatasetMeta {
  dataset_id: string;
  name: string;
  original_filename: string;
  format: string;
  columns: ColumnDef[];
  row_count: number;
  size_bytes: number;
  uploaded_at: string;
}

export interface ConversationTurn {
  turn_id: string;
  role: "user" | "assistant";
  content: string;
  sql?: string | null;
  result_summary?: string | null;
  timestamp: string;
}

export interface QueryResult {
  turn_id: string;
  sql: string;
  columns: string[];
  rows: (string | number | null)[][];
  row_count: number;
  truncated: boolean;
  total_row_count: number;
}

export interface SessionState {
  session_id: string;
  created_at: string;
  last_active_at: string;
  datasets: DatasetMeta[];
  conversation: ConversationTurn[];
  stub_mode?: boolean;
}

export interface ApiError {
  error: string;
  message: string;
}
