import { useState, useCallback } from "react";
import { uploadPDF } from "../lib/api-client";

export function UploadPage({ onUploaded }: { onUploaded: () => void }) {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.endsWith(".pdf")) {
        setMessage("Only PDF files are supported.");
        return;
      }
      setUploading(true);
      setMessage("Uploading and processing...");
      try {
        const result = await uploadPDF(file);
        setMessage(`✓ "${result.filename}" uploaded. ${result.chunk_count} chunks created.`);
        onUploaded();
      } catch (err) {
        setMessage(`Error: ${err}`);
      } finally {
        setUploading(false);
      }
    },
    [onUploaded],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  return (
    <div>
      <h2>Upload PDF</h2>
      <div
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
        style={{
          border: "2px dashed #ccc",
          padding: "40px",
          textAlign: "center",
          cursor: "pointer",
          borderRadius: "8px",
        }}
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <p>Drag &amp; drop a PDF here, or click to select</p>
        <input
          id="file-input"
          type="file"
          accept=".pdf"
          style={{ display: "none" }}
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
      </div>
      {uploading && <p>Processing...</p>}
      {message && <p>{message}</p>}
    </div>
  );
}
