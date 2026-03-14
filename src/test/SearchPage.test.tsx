import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SearchPage } from "../components/SearchPage";
import * as apiClient from "../lib/api-client";

vi.mock("../lib/api-client");

const mockSearch = vi.mocked(apiClient.search);

describe("SearchPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearch.mockResolvedValue([]);
  });

  it("renders search input and button", () => {
    render(<SearchPage />);
    expect(screen.getByPlaceholderText("Ask a question...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search" })).toBeInTheDocument();
  });

  it("does not search when query is empty", async () => {
    render(<SearchPage />);
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(mockSearch).not.toHaveBeenCalled();
  });

  it("displays search results after query", async () => {
    mockSearch.mockResolvedValueOnce([
      { text: "relevant chunk", filename: "doc.pdf", page_number: 2, chunk_index: 1, score: 0.87 },
    ]);
    render(<SearchPage />);
    fireEvent.change(screen.getByPlaceholderText("Ask a question..."), {
      target: { value: "my query" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => {
      expect(screen.getByText("relevant chunk")).toBeInTheDocument();
      expect(screen.getByText(/doc\.pdf/)).toBeInTheDocument();
      expect(screen.getByText(/87\.0%/)).toBeInTheDocument();
    });
  });

  it("triggers search on Enter key", async () => {
    mockSearch.mockResolvedValueOnce([]);
    render(<SearchPage />);
    const input = screen.getByPlaceholderText("Ask a question...");
    fireEvent.change(input, { target: { value: "test query" } });
    fireEvent.keyDown(input, { key: "Enter" });
    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalledWith("test query");
    });
  });

  it("disables button while loading", async () => {
    let resolveSearch!: (v: import("../types").SearchResult[]) => void;
    mockSearch.mockImplementationOnce(
      () => new Promise<import("../types").SearchResult[]>((res) => { resolveSearch = res; }),
    );
    render(<SearchPage />);
    fireEvent.change(screen.getByPlaceholderText("Ask a question..."), {
      target: { value: "query" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(screen.getByRole("button", { name: "Searching..." })).toBeDisabled();
    resolveSearch([]);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Search" })).not.toBeDisabled();
    });
  });
});
