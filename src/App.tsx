import { useState } from "react";
import { LoadingScreen } from "./components/LoadingScreen";
import { UploadPage } from "./components/UploadPage";
import { DocumentsPage } from "./components/DocumentsPage";
import { SearchPage } from "./components/SearchPage";

type Tab = "upload" | "documents" | "search";

export function App() {
  const [ready, setReady] = useState(false);
  const [tab, setTab] = useState<Tab>("upload");
  const [refreshDocs, setRefreshDocs] = useState(0);

  if (!ready) return <LoadingScreen onReady={() => setReady(true)} />;

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", padding: "16px" }}>
      <h1>Mini RAG</h1>
      <nav style={{ display: "flex", gap: "8px", marginBottom: "24px" }}>
        {(["upload", "documents", "search"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{ fontWeight: tab === t ? "bold" : "normal" }}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </nav>
      {tab === "upload" && <UploadPage onUploaded={() => setRefreshDocs((r) => r + 1)} />}
      {tab === "documents" && <DocumentsPage key={refreshDocs} />}
      {tab === "search" && <SearchPage />}
    </div>
  );
}

export default App;
