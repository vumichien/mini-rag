import { useEffect, useState } from "react";
import { checkHealth } from "../lib/api-client";

interface Props {
  onReady: () => void;
}

export function LoadingScreen({ onReady }: Props) {
  const [status, setStatus] = useState("Starting up...");

  useEffect(() => {
    const start = Date.now();
    const interval = setInterval(async () => {
      const secs = Math.floor((Date.now() - start) / 1000);

      if (secs > 60) {
        setStatus("Startup timeout. Please restart the app.");
        clearInterval(interval);
        return;
      }

      const ok = await checkHealth();
      if (ok) {
        clearInterval(interval);
        onReady();
      } else {
        setStatus(`Starting up... (${secs}s)`);
      }
    }, 500);
    return () => clearInterval(interval);
  }, [onReady]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        gap: "16px",
      }}
    >
      <div className="spinner" />
      <p>{status}</p>
    </div>
  );
}
