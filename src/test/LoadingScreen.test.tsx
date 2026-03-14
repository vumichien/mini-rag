import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { LoadingScreen } from "../components/LoadingScreen";
import * as apiClient from "../lib/api-client";

vi.mock("../lib/api-client");

const mockCheckHealth = vi.mocked(apiClient.checkHealth);

// Helper: flush one interval tick (500ms) + all pending microtasks
async function tickInterval() {
  await act(async () => {
    vi.advanceTimersByTime(500);
    await vi.runAllTimersAsync();
  });
}

describe("LoadingScreen", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders starting up message initially", () => {
    mockCheckHealth.mockResolvedValue(false);
    render(<LoadingScreen onReady={() => {}} />);
    expect(screen.getByText("Starting up...")).toBeInTheDocument();
  });

  it("calls onReady when health check succeeds", async () => {
    const onReady = vi.fn();
    mockCheckHealth.mockResolvedValue(true);
    render(<LoadingScreen onReady={onReady} />);
    await tickInterval();
    expect(onReady).toHaveBeenCalledTimes(1);
  });

  it("keeps polling while health check fails", async () => {
    mockCheckHealth.mockResolvedValue(false);
    render(<LoadingScreen onReady={() => {}} />);
    await tickInterval();
    await tickInterval();
    await tickInterval();
    expect(mockCheckHealth.mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("shows timeout message after 30s", async () => {
    mockCheckHealth.mockResolvedValue(false);
    // Set Date.now to return a fixed start time, then override it to simulate 31s elapsed
    const startTime = 1_000_000;
    let currentTime = startTime;
    vi.spyOn(Date, "now").mockImplementation(() => currentTime);

    render(<LoadingScreen onReady={() => {}} />);

    // Simulate 31 seconds have passed so secs > 30 triggers on next tick
    currentTime = startTime + 31_500;
    await tickInterval();

    expect(screen.getByText("Startup timeout. Please restart the app.")).toBeInTheDocument();
  });
});
