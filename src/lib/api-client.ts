import type { Document, SearchResult, UploadResponse } from "../types";

const API_BASE = "http://127.0.0.1:52547";

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

export async function uploadPDF(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<UploadResponse>;
}

export async function getDocuments(): Promise<Document[]> {
  const res = await fetch(`${API_BASE}/documents`);
  const data = await res.json() as { documents: Document[] };
  return data.documents;
}

export async function deleteDocument(doc_id: string): Promise<void> {
  await fetch(`${API_BASE}/documents/${doc_id}`, { method: "DELETE" });
}

export async function search(query: string): Promise<SearchResult[]> {
  const res = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, n_results: 5 }),
  });
  const data = await res.json() as { results: SearchResult[] };
  return data.results;
}
