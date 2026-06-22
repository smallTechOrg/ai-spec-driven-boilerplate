import type { SessionState, DatasetMeta, QueryResult } from "./types";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "unknown", message: res.statusText }));
    throw Object.assign(new Error(err.message || res.statusText), { code: err.error, status: res.status });
  }
  return res.json();
}

export const apiClient = {
  createSession: () =>
    request<{ session_id: string; created_at: string }>("/api/sessions", { method: "POST" }),

  getCurrentSession: () =>
    request<SessionState & { stub_mode: boolean }>("/api/sessions/current"),

  uploadDataset: (file: File): Promise<DatasetMeta> => {
    const form = new FormData();
    form.append("file", file);
    return fetch("/api/datasets", {
      method: "POST",
      credentials: "include",
      body: form,
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res
          .json()
          .catch(() => ({ error: "upload_failed", message: res.statusText }));
        throw Object.assign(new Error(err.message), { code: err.error, status: res.status });
      }
      return res.json();
    });
  },

  query: (question: string): Promise<QueryResult> =>
    request<QueryResult>("/api/query", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  getAudit: (limit = 50) =>
    request<{ entries: unknown[]; total: number }>(`/api/audit?limit=${limit}`),
};
