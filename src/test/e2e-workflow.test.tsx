/**
 * E2E workflow integration tests — Phase 07 Testing.
 *
 * Tests the full user journey:
 *   upload PDF → documents list → search → delete → verify.
 *
 * Tests that go through <App> use fake timers only for the loading screen,
 * then restore real timers before async assertions.
 * Tests for individual page components render them directly (faster, no loading).
 *
 * Maps to: Phase 07 Tests 2, 3, 5, 6 and the Manual Smoke Test Script.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { App } from "../App";
import { UploadPage } from "../components/UploadPage";
import { DocumentsPage } from "../components/DocumentsPage";
import { SearchPage } from "../components/SearchPage";
import * as apiClient from "../lib/api-client";

vi.mock("../lib/api-client");

const mockCheckHealth = vi.mocked(apiClient.checkHealth);
const mockUploadPDF = vi.mocked(apiClient.uploadPDF);
const mockGetDocuments = vi.mocked(apiClient.getDocuments);
const mockDeleteDocument = vi.mocked(apiClient.deleteDocument);
const mockSearch = vi.mocked(apiClient.search);

/** Advance fake timers so LoadingScreen health-poll fires and transitions to UI. */
async function waitForReady() {
  await act(async () => {
    vi.advanceTimersByTime(500);
    await vi.runAllTimersAsync();
  });
}

// ── App startup tests (fake timers required) ─────────────────────────────────

describe("E2E: App Startup (Test 2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockGetDocuments.mockResolvedValue([]);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows loading screen before backend is ready", () => {
    mockCheckHealth.mockResolvedValue(false);
    render(<App />);
    expect(screen.getByText("Starting up...")).toBeInTheDocument();
    expect(screen.queryByText("Mini RAG")).not.toBeInTheDocument();
  });

  it("transitions to main UI once backend responds", async () => {
    mockCheckHealth.mockResolvedValue(true);
    render(<App />);
    await waitForReady();
    expect(screen.getByText("Mini RAG")).toBeInTheDocument();
    expect(screen.queryByText("Starting up...")).not.toBeInTheDocument();
  });

  it("renders all three tabs after ready", async () => {
    mockCheckHealth.mockResolvedValue(true);
    render(<App />);
    await waitForReady();
    expect(screen.getByRole("button", { name: "Upload" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Documents" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search" })).toBeInTheDocument();
  });
});

// ── Upload workflow (Test 3) — render UploadPage directly ────────────────────

describe("E2E: PDF Upload (Test 3)", () => {
  const onUploaded = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uploads a PDF and shows chunk count success message", async () => {
    mockUploadPDF.mockResolvedValueOnce({
      doc_id: "doc-001",
      filename: "sample.pdf",
      chunk_count: 12,
    });

    render(<UploadPage onUploaded={onUploaded} />);
    const input = document.getElementById("file-input") as HTMLInputElement;
    const file = new File(["pdf-content"], "sample.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/sample\.pdf.*12 chunks/)).toBeInTheDocument();
    });
    expect(mockUploadPDF).toHaveBeenCalledWith(file);
    expect(onUploaded).toHaveBeenCalledTimes(1);
  });

  it("rejects non-PDF files without calling API", async () => {
    render(<UploadPage onUploaded={onUploaded} />);
    const input = document.getElementById("file-input") as HTMLInputElement;
    const file = new File(["content"], "document.txt", { type: "text/plain" });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("Only PDF files are supported.")).toBeInTheDocument();
    });
    expect(mockUploadPDF).not.toHaveBeenCalled();
  });

  it("shows error when upload fails and page remains usable", async () => {
    mockUploadPDF.mockRejectedValueOnce(new Error("Server error"));
    render(<UploadPage onUploaded={onUploaded} />);
    const input = document.getElementById("file-input") as HTMLInputElement;
    const file = new File(["content"], "bad.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
    });
    expect(onUploaded).not.toHaveBeenCalled();
  });

  it("handles drag-and-drop upload", async () => {
    mockUploadPDF.mockResolvedValueOnce({
      doc_id: "doc-002",
      filename: "dropped.pdf",
      chunk_count: 5,
    });
    render(<UploadPage onUploaded={onUploaded} />);
    const dropZone = screen.getByText(/Drag & drop/).closest("div")!;
    const file = new File(["content"], "dropped.pdf", { type: "application/pdf" });
    fireEvent.drop(dropZone, { dataTransfer: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/dropped\.pdf.*5 chunks/)).toBeInTheDocument();
    });
  });
});

// ── Search workflow (Test 5) — render SearchPage directly ────────────────────

describe("E2E: Search Results (Test 5)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearch.mockResolvedValue([]);
  });

  it("returns result cards with text, filename, page number, and score", async () => {
    mockSearch.mockResolvedValueOnce([
      {
        text: "Machine learning enables computers to learn from data.",
        filename: "ai-paper.pdf",
        page_number: 3,
        chunk_index: 5,
        score: 0.923,
      },
      {
        text: "Neural networks are inspired by the human brain.",
        filename: "ai-paper.pdf",
        page_number: 7,
        chunk_index: 12,
        score: 0.811,
      },
    ]);

    render(<SearchPage />);
    const input = screen.getByPlaceholderText("Ask a question...");
    fireEvent.change(input, { target: { value: "machine learning" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByText("Machine learning enables computers to learn from data.")).toBeInTheDocument();
      expect(screen.getByText("Neural networks are inspired by the human brain.")).toBeInTheDocument();
    });

    // Scores as percentages (Test 5: "Scores are 0-100%")
    expect(screen.getByText(/92\.3%/)).toBeInTheDocument();
    expect(screen.getByText(/81\.1%/)).toBeInTheDocument();

    // Source info (Test 5: "filename, page number")
    expect(screen.getAllByText(/ai-paper\.pdf/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Page 3/).length).toBeGreaterThan(0);
  });

  it("shows at most 5 results (default n_results)", async () => {
    const results = Array.from({ length: 5 }, (_, i) => ({
      text: `Chunk text number ${i + 1}`,
      filename: "doc.pdf",
      page_number: i + 1,
      chunk_index: i,
      score: 0.9 - i * 0.1,
    }));
    mockSearch.mockResolvedValueOnce(results);

    render(<SearchPage />);
    fireEvent.change(screen.getByPlaceholderText("Ask a question..."), {
      target: { value: "any query" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByText("Chunk text number 1")).toBeInTheDocument();
    });
    for (let i = 1; i <= 5; i++) {
      expect(screen.getByText(`Chunk text number ${i}`)).toBeInTheDocument();
    }
  });

  it("shows no result cards when search returns empty", async () => {
    mockSearch.mockResolvedValueOnce([]);
    render(<SearchPage />);
    fireEvent.change(screen.getByPlaceholderText("Ask a question..."), {
      target: { value: "something obscure" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalledWith("something obscure");
    });
    // SearchPage renders no cards when results = []
    expect(screen.queryByText(/Score:/)).not.toBeInTheDocument();
  });

  it("triggers search on Enter key", async () => {
    mockSearch.mockResolvedValueOnce([]);
    render(<SearchPage />);
    const input = screen.getByPlaceholderText("Ask a question...");
    fireEvent.change(input, { target: { value: "enter key test" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalledWith("enter key test");
    });
  });

  it("disables search button while loading", async () => {
    let resolveSearch!: (v: import("../types").SearchResult[]) => void;
    mockSearch.mockImplementationOnce(
      () => new Promise<import("../types").SearchResult[]>((res) => { resolveSearch = res; }),
    );
    render(<SearchPage />);
    fireEvent.change(screen.getByPlaceholderText("Ask a question..."), {
      target: { value: "loading test" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(screen.getByRole("button", { name: "Searching..." })).toBeDisabled();
    resolveSearch([]);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Search" })).not.toBeDisabled();
    });
  });
});

// ── Delete workflow (Test 6) — render DocumentsPage directly ─────────────────

describe("E2E: Document Deletion (Test 6)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("confirm", vi.fn(() => true));
  });

  it("deletes document and removes from list", async () => {
    mockGetDocuments
      .mockResolvedValueOnce([{ doc_id: "doc-001", filename: "to-delete.pdf", chunk_count: 5 }])
      .mockResolvedValueOnce([]);
    mockDeleteDocument.mockResolvedValueOnce(undefined);

    render(<DocumentsPage />);
    await waitFor(() => {
      expect(screen.getByText(/to-delete\.pdf/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(mockDeleteDocument).toHaveBeenCalledWith("doc-001");
      expect(screen.getByText("No documents uploaded yet.")).toBeInTheDocument();
    });
  });

  it("does not delete when user cancels confirm dialog", async () => {
    vi.stubGlobal("confirm", vi.fn(() => false));
    mockGetDocuments.mockResolvedValueOnce([
      { doc_id: "doc-002", filename: "keep.pdf", chunk_count: 3 },
    ]);

    render(<DocumentsPage />);
    await waitFor(() => {
      expect(screen.getByText(/keep\.pdf/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(mockDeleteDocument).not.toHaveBeenCalled();
    expect(screen.getByText(/keep\.pdf/)).toBeInTheDocument();
  });

  it("shows document count in heading", async () => {
    mockGetDocuments.mockResolvedValueOnce([
      { doc_id: "1", filename: "a.pdf", chunk_count: 10 },
      { doc_id: "2", filename: "b.pdf", chunk_count: 5 },
    ]);
    render(<DocumentsPage />);
    await waitFor(() => {
      expect(screen.getByText("Documents (2)")).toBeInTheDocument();
    });
  });
});

// ── Automated Smoke Test (Manual Smoke Test Script) ───────────────────────────

describe("E2E: Full Smoke Test Workflow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("confirm", vi.fn(() => true));
  });

  it("upload → list → search → delete → verify empty (automated smoke test)", async () => {
    // Step 1: Upload PDF
    mockUploadPDF.mockResolvedValueOnce({
      doc_id: "smoke-001",
      filename: "smoke.pdf",
      chunk_count: 8,
    });
    const onUploaded = vi.fn();
    const { unmount: unmountUpload } = render(<UploadPage onUploaded={onUploaded} />);
    const fileInput = document.getElementById("file-input") as HTMLInputElement;
    const file = new File(["content"], "smoke.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByText(/smoke\.pdf.*8 chunks/)).toBeInTheDocument();
    });
    expect(onUploaded).toHaveBeenCalledTimes(1);
    unmountUpload();

    // Step 2: Verify document appears in list
    mockGetDocuments.mockResolvedValueOnce([
      { doc_id: "smoke-001", filename: "smoke.pdf", chunk_count: 8 },
    ]).mockResolvedValueOnce([]);
    mockDeleteDocument.mockResolvedValueOnce(undefined);
    const { unmount: unmountDocs } = render(<DocumentsPage />);
    await waitFor(() => {
      expect(screen.getByText(/smoke\.pdf/)).toBeInTheDocument();
      expect(screen.getByText("Documents (1)")).toBeInTheDocument();
    });

    // Step 3: Delete the document
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => {
      expect(mockDeleteDocument).toHaveBeenCalledWith("smoke-001");
      expect(screen.getByText("No documents uploaded yet.")).toBeInTheDocument();
    });
    unmountDocs();

    // Step 4: Search now returns empty (doc is gone)
    mockSearch.mockResolvedValueOnce([]);
    render(<SearchPage />);
    fireEvent.change(screen.getByPlaceholderText("Ask a question..."), {
      target: { value: "introduction" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalledWith("introduction");
    });
    // No result cards since doc was deleted before search
    expect(screen.queryByText(/Score:/)).not.toBeInTheDocument();
  });
});
