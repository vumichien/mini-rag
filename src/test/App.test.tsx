import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { App } from "../App";
import * as apiClient from "../lib/api-client";

vi.mock("../lib/api-client");

const mockCheckHealth = vi.mocked(apiClient.checkHealth);
const mockGetDocuments = vi.mocked(apiClient.getDocuments);

/** Advance 500ms to trigger LoadingScreen's first interval tick */
async function triggerReady() {
  await act(async () => {
    vi.advanceTimersByTime(500);
    await vi.runAllTimersAsync();
  });
}

describe("App", () => {
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

  it("transitions to main UI when backend is ready", async () => {
    mockCheckHealth.mockResolvedValue(true);
    render(<App />);
    await triggerReady();
    expect(screen.getByText("Mini RAG")).toBeInTheDocument();
  });

  it("renders tab navigation after ready", async () => {
    mockCheckHealth.mockResolvedValue(true);
    render(<App />);
    await triggerReady();
    expect(screen.getByRole("button", { name: "Upload" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Documents" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search" })).toBeInTheDocument();
  });

  it("switches tabs on click", async () => {
    mockCheckHealth.mockResolvedValue(true);
    render(<App />);
    await triggerReady();
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(screen.getByPlaceholderText("Ask a question...")).toBeInTheDocument();
  });
});
