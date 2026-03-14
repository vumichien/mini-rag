import { useEffect, useState, useCallback } from "react";
import { getDocuments, deleteDocument } from "../lib/api-client";
import type { Document } from "../types";

export function DocumentsPage() {
  const [docs, setDocs] = useState<Document[]>([]);

  const load = useCallback(async () => {
    setDocs(await getDocuments());
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleDelete = async (doc_id: string) => {
    if (!confirm("Delete this document and all its chunks?")) return;
    await deleteDocument(doc_id);
    await load();
  };

  return (
    <div>
      <h2>Documents ({docs.length})</h2>
      {docs.length === 0 && <p>No documents uploaded yet.</p>}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {docs.map((doc) => (
          <li
            key={doc.doc_id}
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "8px 0",
              borderBottom: "1px solid #eee",
            }}
          >
            <span>
              {doc.filename} <small>({doc.chunk_count} chunks)</small>
            </span>
            <button onClick={() => handleDelete(doc.doc_id)}>Delete</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
