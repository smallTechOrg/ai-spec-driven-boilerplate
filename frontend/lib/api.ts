const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export async function apiFetch(path: string, opts?: RequestInit) {
  const r = await fetch(`${API_URL}${path}`, opts);
  return r;
}

export { API_URL };
