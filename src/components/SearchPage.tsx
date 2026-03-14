import { useState } from "react";
import { search } from "../lib/api-client";
import type { SearchResult } from "../types";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      setResults(await search(query));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Search</h2>
      <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void handleSearch()}
          placeholder="Ask a question..."
          style={{ flex: 1, padding: "8px" }}
        />
        <button onClick={() => void handleSearch()} disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </button>
      </div>
      {results.map((r, i) => (
        <div
          key={i}
          style={{
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "12px",
            marginBottom: "12px",
          }}
        >
          <div style={{ fontSize: "12px", color: "#888", marginBottom: "8px" }}>
            {r.filename} · Page {r.page_number} · Score: {(r.score * 100).toFixed(1)}%
          </div>
          <p style={{ margin: 0 }}>{r.text}</p>
        </div>
      ))}
    </div>
  );
}
