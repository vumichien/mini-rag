import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { DocumentsPage } from "../components/DocumentsPage";
import * as apiClient from "../lib/api-client";

vi.mock("../lib/api-client");

const mockGetDocuments = vi.mocked(apiClient.getDocuments);
const mockDeleteDocument = vi.mocked(apiClient.deleteDocument);

describe("DocumentsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Stub confirm globally
    vi.stubGlobal("confirm", vi.fn(() => true));
  });

  it("shows empty state when no documents", async () => {
    mockGetDocuments.mockResolvedValueOnce([]);
    render(<DocumentsPage />);
    await waitFor(() => {
      expect(screen.getByText("No documents uploaded yet.")).toBeInTheDocument();
    });
  });

  it("renders document list", async () => {
    mockGetDocuments.mockResolvedValueOnce([
      { doc_id: "1", filename: "report.pdf", chunk_count: 7 },
      { doc_id: "2", filename: "notes.pdf", chunk_count: 2 },
    ]);
    render(<DocumentsPage />);
    await waitFor(() => {
      expect(screen.getByText(/report\.pdf/)).toBeInTheDocument();
      expect(screen.getByText(/notes\.pdf/)).toBeInTheDocument();
      expect(screen.getByText(/7 chunks/)).toBeInTheDocument();
    });
  });

  it("shows document count in heading", async () => {
    mockGetDocuments.mockResolvedValueOnce([
      { doc_id: "1", filename: "a.pdf", chunk_count: 1 },
    ]);
    render(<DocumentsPage />);
    await waitFor(() => {
      expect(screen.getByText("Documents (1)")).toBeInTheDocument();
    });
  });

  it("deletes a document on confirm", async () => {
    mockGetDocuments
      .mockResolvedValueOnce([{ doc_id: "1", filename: "a.pdf", chunk_count: 5 }])
      .mockResolvedValueOnce([]);
    mockDeleteDocument.mockResolvedValueOnce(undefined);
    render(<DocumentsPage />);
    await waitFor(() => {
      expect(screen.getByText(/a\.pdf/)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => {
      expect(mockDeleteDocument).toHaveBeenCalledWith("1");
      expect(screen.getByText("No documents uploaded yet.")).toBeInTheDocument();
    });
  });

  it("does not delete when user cancels confirm", async () => {
    vi.stubGlobal("confirm", vi.fn(() => false));
    mockGetDocuments.mockResolvedValueOnce([
      { doc_id: "1", filename: "a.pdf", chunk_count: 5 },
    ]);
    render(<DocumentsPage />);
    await waitFor(() => {
      expect(screen.getByText(/a\.pdf/)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(mockDeleteDocument).not.toHaveBeenCalled();
  });
});
