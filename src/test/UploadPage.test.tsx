import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { UploadPage } from "../components/UploadPage";
import * as apiClient from "../lib/api-client";

vi.mock("../lib/api-client");

const mockUploadPDF = vi.mocked(apiClient.uploadPDF);

describe("UploadPage", () => {
  const onUploaded = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders drop zone and heading", () => {
    render(<UploadPage onUploaded={onUploaded} />);
    expect(screen.getByText("Upload PDF")).toBeInTheDocument();
    expect(screen.getByText(/Drag & drop/)).toBeInTheDocument();
  });

  it("shows error for non-PDF files", async () => {
    render(<UploadPage onUploaded={onUploaded} />);
    const input = document.getElementById("file-input") as HTMLInputElement;
    const file = new File(["content"], "document.txt", { type: "text/plain" });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByText("Only PDF files are supported.")).toBeInTheDocument();
    });
    expect(mockUploadPDF).not.toHaveBeenCalled();
  });

  it("uploads a PDF file and shows success message", async () => {
    mockUploadPDF.mockResolvedValueOnce({
      doc_id: "123",
      filename: "test.pdf",
      chunk_count: 10,
    });
    render(<UploadPage onUploaded={onUploaded} />);
    const input = document.getElementById("file-input") as HTMLInputElement;
    const file = new File(["content"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByText(/test\.pdf.*10 chunks/)).toBeInTheDocument();
    });
    expect(onUploaded).toHaveBeenCalledTimes(1);
  });

  it("shows error message on upload failure", async () => {
    mockUploadPDF.mockRejectedValueOnce(new Error("Server error"));
    render(<UploadPage onUploaded={onUploaded} />);
    const input = document.getElementById("file-input") as HTMLInputElement;
    const file = new File(["content"], "fail.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
    });
    expect(onUploaded).not.toHaveBeenCalled();
  });

  it("handles drag-and-drop with a PDF", async () => {
    mockUploadPDF.mockResolvedValueOnce({
      doc_id: "456",
      filename: "dropped.pdf",
      chunk_count: 3,
    });
    render(<UploadPage onUploaded={onUploaded} />);
    const dropZone = screen.getByText(/Drag & drop/).closest("div")!;
    const file = new File(["content"], "dropped.pdf", { type: "application/pdf" });
    fireEvent.drop(dropZone, { dataTransfer: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByText(/dropped\.pdf.*3 chunks/)).toBeInTheDocument();
    });
  });
});
