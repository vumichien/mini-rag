export interface Document {
  doc_id: string;
  filename: string;
  chunk_count: number;
}

export interface SearchResult {
  text: string;
  filename: string;
  page_number: number;
  chunk_index: number;
  score: number;
}

export interface UploadResponse {
  doc_id: string;
  filename: string;
  chunk_count: number;
}
